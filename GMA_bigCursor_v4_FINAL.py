
# GMA_bigCursor_v4.py
# gamos 05/06/2019 (DD/MM/YY format)

# A function to calculate timber volumes within a VRI, THLB and (whatever else) intersect.

import arcpy, sys, os, time, datetime
from arcpy import env
arcpy.env.overwriteOutput = True
arcpy.ClearWorkspaceCache_management()

wrkSpc_T = r"T:\temp.gdb"
arcpy.env.workspace = wrkSpc_T

#################################################################################
# A really extensive update cursor to get volumes of the various species ranks!!! Works with THLB or CFLB.
# 'inputFC' must include fields from either Crown Forest Land Basen or Timber Harvesting land Base FCs.
# Calculations for total volume, density, and volume per species rank per polygon are written to the 'z' fields.

def bigCursor (inputFC, THLB_type):
    startTime  = time.clock()
    # 'inputFC' must be a VRI feature class
    cflb_Dict = {"THLB":"THLB_FACT", "CFLB":"CFLB_INC_FACT"}
    zeroVolumes = []

      #Execute the bigCursor on your inputFC
    fields = ["SPECIES_CD_1", "LIVE_VOL_PER_HA_SPP1_125","DEAD_STAND_VOLUME_125","LIVE_VOL_PER_HA_SPP1_175",\
    "DEAD_STAND_VOLUME_175","SPECIES_CD_2","LIVE_VOL_PER_HA_SPP2_125","LIVE_VOL_PER_HA_SPP2_175","SPECIES_CD_3","SPECIES_CD_4","SPECIES_CD_5",\
    "SPECIES_CD_6","LIVE_VOL_PER_HA_SPP3_125","LIVE_VOL_PER_HA_SPP4_125", "LIVE_VOL_PER_HA_SPP5_125","LIVE_VOL_PER_HA_SPP6_125","LIVE_VOL_PER_HA_SPP3_175",\
    "LIVE_VOL_PER_HA_SPP4_175", "LIVE_VOL_PER_HA_SPP5_175","LIVE_VOL_PER_HA_SPP6_175","VRI_DEAD_STEMS_PER_HA","VRI_LIVE_STEMS_PER_HA"] # replaced "CFLB_INC_FACT" with "THLB_FACT"
    areaField, oidField = str(arcpy.Describe(inputFC).areaFieldName), str(arcpy.Describe(inputFC).OIDFieldName)

    for fld in [areaField, oidField, cflb_Dict[THLB_type]]:
##        print fld
        fields.append(fld)

    fieldsToAdd = ["Hectares", "z_LIVE_SPECIES_1_m3","z_DEAD_STAND_VOLUME_m3","z_LIVE_SPECIES_2_m3","z_LIVE_SPECIES_3_m3",\
                    "z_LIVE_SPECIES_4_m3","z_LIVE_SPECIES_5_m3","z_LIVE_SPECIES_6_m3", "z_TOTAL_VOLUME","z_VOLUME_PER_HECTARE"]

    for fld in fieldsToAdd:
        if fld not in [str(f.name) for f in arcpy.ListFields(inputFC)]: # list of the existing fields in inputFC
            arcpy.AddField_management(inputFC, fld ,"DOUBLE") # creates the various 'z_LIVE_SPECIES' and 'z_DEAD_STAND_VOLUME' fields
        fields.append(fld)
    arcpy.AddField_management(inputFC, "NO_VOLUME_flag", "TEXT") # add a lone text field, the NO VOLUME flag (to indicate where the sum of all "z_LIVE_SPECIES_..._m3" fields is 0.0
    fields.append("NO_VOLUME_flag")
    print("Total of {} new fields added to the FC: {}.".format(len(fields) , str(inputFC)))

    for count, f in enumerate(fields):
        print("{}.\t{}".format(count, f))

    print("\nNow Running update cursor to update the area_ha field and calculate the various z_....._m3 fields..")

    with arcpy.da.UpdateCursor(inputFC, fields) as ucursor:
        for count, row in enumerate(ucursor):
##            conditions_with_small_poly_delete = [row[fields.index("SPECIES_CD_1")] is None, row[fields.index("SPECIES_CD_1")] == "", row[fields.index(areaField)] < 1000.0]
            conditions = [row[fields.index("SPECIES_CD_1")] is None, row[fields.index("SPECIES_CD_1")] == ""]
            if any(conditions):
                 ucursor.deleteRow()   # So delete these rows, they do not help with analysis.
                 continue

            row[fields.index("Hectares")] = row[fields.index(areaField)] * 0.0001 # calculate the 'Hectares' field
            if row[fields.index("VRI_DEAD_STEMS_PER_HA")] is None: # Set the VRI live and dead stems to 0 if there's a Null value in there
                row[fields.index("VRI_DEAD_STEMS_PER_HA")]  = 0.0     # (a null value will screw up MakeFeatureLayer SQL where clause later on)
            if row[fields.index("VRI_LIVE_STEMS_PER_HA")]  is None:
                row[fields.index("VRI_LIVE_STEMS_PER_HA")]  = 0.0

            # Calculate species 1 live and dead volumes.
            if row[fields.index("SPECIES_CD_1")]  == 'PL' or row[fields.index("SPECIES_CD_1")]  == 'PLI':  #If species 1 is pine ..
##            if row[fields.index("SPECIES_CD_1")] LIKE 'PL%': # try this ?
                if row[fields.index("LIVE_VOL_PER_HA_SPP1_125")]  is None:
                    row[fields.index("LIVE_VOL_PER_HA_SPP1_125")]  = 0.0
                row[fields.index("z_LIVE_SPECIES_1_m3")]  =  row[fields.index("Hectares")]  * row[fields.index("LIVE_VOL_PER_HA_SPP1_125")] * row[fields.index(cflb_Dict[THLB_type])]  # multiply by "THLB_FACT" row[fields.index("THLB_FACT")]  because in the CFLB
                if row[fields.index("DEAD_STAND_VOLUME_125")] :  # Because there are some NULL values to deal with in DEAD_STAND_VOLUME_125
                    row[fields.index("z_DEAD_STAND_VOLUME_m3")] = row[fields.index("Hectares")] * row[fields.index("DEAD_STAND_VOLUME_125")]
                else:
                    row[fields.index("z_DEAD_STAND_VOLUME_m3")] = 0.0 # Makes this value a float in case it's not already (but it should be because the field is a float).

            else:   # If species 1 is not pine ..
                if row[fields.index("LIVE_VOL_PER_HA_SPP1_175")] is None: # in cases where SPECIES_CD_1 is Null,  LIVE_VOL_PER_HA_SPP1_175 is also Null
                    row[fields.index("LIVE_VOL_PER_HA_SPP1_175")] = 0.0
                row[fields.index("z_LIVE_SPECIES_1_m3")]  =  row[fields.index("Hectares")] * row[fields.index("LIVE_VOL_PER_HA_SPP1_175")] * row[fields.index(cflb_Dict[THLB_type])]
##                row[fields.index("z_LIVE_SPECIES_1_m3")]  =  row[fields.index("SPECIES_CD_1")] *row[fields.index("LIVE_VOL_PER_HA_SPP1_175")]*row[fields.index("THLB_FACT")]  #Checked: there are no possible NULL values to deal with in LIVE_VOL_PER_HA_SPP1_175

                if row[fields.index("DEAD_STAND_VOLUME_175")]:     # Because there are some NULL values to deal with in DEAD_STAND_VOLUME_175
                    row[fields.index("z_DEAD_STAND_VOLUME_m3")] =  row[fields.index("Hectares")] * row[fields.index("DEAD_STAND_VOLUME_175")]
                else:
                    row[fields.index("z_DEAD_STAND_VOLUME_m3")] = 0.0

            # Calculate species 2-6 live volumes.
            for x in range (2,7):
##            for x in ["2", "3", "4", "5", "6", "7"]:
                speciesX = fields.index("SPECIES_CD_"+ str(x))  # these 4 variables are all integers..
                zliveSpeciesX = fields.index("z_LIVE_SPECIES_" + str(x) + "_m3")
                liveVol125x = fields.index("LIVE_VOL_PER_HA_SPP" + str(x) + "_125")
                liveVol175x = fields.index("LIVE_VOL_PER_HA_SPP" + str(x) + "_175")

                if row[speciesX] in ['PL', 'PLI']: # If species (2-6) is PL or PLI
                            if row[liveVol125x]:
##                                row[zliveSpeciesX] = row[fields.index("SPECIES_CD_1")] * row[fields.index("THLB_FACT")] * row[liveVol125x]
                                row[zliveSpeciesX] = row[fields.index("Hectares")] * row[liveVol125x] * row[fields.index(cflb_Dict[THLB_type])]
                            else:
                                 row[zliveSpeciesX] = 0.0

                elif row[speciesX] and row[speciesX] not in ['PLI', 'PL', 'PA', 'AC', 'ACT', 'AT', 'EP']: # this is a list of mainly undesirable species
                    if row[liveVol175x]:
                          row[zliveSpeciesX] = row[fields.index("Hectares")] * row[liveVol175x]
                    else:
                          row[zliveSpeciesX] = 0.0

                else:
                    row[zliveSpeciesX] = 0.0 # i.e. if SPECIES_CD_(2-6) == None or if it's one of the undesirable species above..

##            print("{} is: {}".format("z_LIVE_SPECIES_1_m3", row[fields.index("z_LIVE_SPECIES_1_m3")]))
##            print("{} is: {}".format("z_LIVE_SPECIES_2_m3", row[fields.index("z_LIVE_SPECIES_2_m3")]))
##            print("{} is: {}".format("z_LIVE_SPECIES_3_m3", row[fields.index("z_LIVE_SPECIES_3_m3")]))
##            print("{} is: {}".format("z_LIVE_SPECIES_4_m3", row[fields.index("z_LIVE_SPECIES_4_m3")]))
##            print("{} is: {}".format("z_LIVE_SPECIES_5_m3", row[fields.index("z_LIVE_SPECIES_5_m3")]))
##            print("{} is: {}".format("z_LIVE_SPECIES_6_m3", row[fields.index("z_LIVE_SPECIES_6_m3")]))
##            print("{} is: {}".format("z_DEAD_STAND_VOLUME_m3", row[fields.index("z_DEAD_STAND_VOLUME_m3")]))

            ####################################
            # Calculate total volume per polygon, and volume per hectare in each polygon:
            row[fields.index("z_TOTAL_VOLUME")] =  row[fields.index("z_LIVE_SPECIES_1_m3")]  +  row[fields.index("z_DEAD_STAND_VOLUME_m3")] +  row[fields.index("z_LIVE_SPECIES_2_m3")] + row[fields.index("z_LIVE_SPECIES_3_m3")]  +  row[fields.index("z_LIVE_SPECIES_4_m3")]  +  row[fields.index("z_LIVE_SPECIES_5_m3")]  +  row[fields.index("z_LIVE_SPECIES_6_m3")]  # total volume per polygon
            #row[14]= row[fields.index("z_LIVE_SPECIES_1_m3")]  + row[7] + row.z_LIVE_SPECIES_2_m3 + row.z_LIVE_SPECIES_3_m3 + row.z_LIVE_SPECIES_4_m3 + row.z_LIVE_SPECIES_5_m3 + row.z_LIVE_SPECIES_6_m3
            row[fields.index("z_VOLUME_PER_HECTARE")] = row[fields.index("z_TOTAL_VOLUME")] / row[fields.index("Hectares")]  # volume per hectare in each polygon (note: float division)

            a, b = row[fields.index("Hectares")], row[fields.index("z_VOLUME_PER_HECTARE")]
##            print("Polygon is {:.1f} ha and has {} m3/ha.\n".format(a, b))
            if b == 0.0:
                zeroVolumes.append(row[fields.index("OBJECTID")])
                row[fields.index("NO_VOLUME_flag")] = "No volume"
            ucursor.updateRow(row)
    endTime  = time.clock()
##    print("UpdateCursor completed. Hectares updated from area field; individual species and total volume (z_..._m3) fields created and calculated.")

    print("\nUpdateCursor on {} finished in {:.1f} minutes / {} seconds. Hectares updated from {}; individual species and total volume (z_..._m3)\
fields created and calculated. \nTotal of {} polygons with {} zero volume polygons.\n".format( inputFC, ((endTime - startTime)/60.0 ), int(endTime - startTime), areaField, count, len(zeroVolumes)))

    # Calculate total volume and density across the 'inputFC' via Statistics_analysis and a searchCursor
    outTbl, statsFields, caseField = arcpy.Describe(inputFC).baseName + "_stats", [["Hectares","SUM"],["z_TOTAL_VOLUME", "SUM"]], "NO_VOLUME_flag"
    arcpy.Statistics_analysis (inputFC, outTbl, statsFields, caseField)

    fields = [s[1] + "_" + s[0] for s in statsFields] # converts [["Hectares","SUM"],["z_TOTAL_VOLUME", "SUM"]] into ['SUM_Hectares', 'SUM_z_TOTAL_VOLUME']
    rowCount = 0
    with arcpy.da.SearchCursor(outTbl, fields) as ucursor:
        for row in ucursor:
            if row[fields.index('SUM_z_TOTAL_VOLUME')] > 0:
                total_vol = row[fields.index('SUM_z_TOTAL_VOLUME')]
                total_ha = row[fields.index('SUM_Hectares')]
                total_m3_per_ha = total_vol / total_ha
                rowCount += 1
        print("{} row(s) processed where row[fields.index('SUM_z_TOTAL_VOLUME')] > 0".format(rowCount))
    print("FC: {} has {:.1f} m3 timber volume on {:.1f} ha, thus timber density is {:.1f} m3/ha, based on {} polygons with volume.".format(inputFC, total_vol, total_ha, total_m3_per_ha, count - len(zeroVolumes)))

# FUNCTION CALL HERE
##inputFC is an intersect between VRI and THLB in your area of interest, plus any other layers you want to
## intersect (for better spatial extents)
## ex. W:\FOR\RSI\DKL\General_User_Data\gamos\Layer_files_and_MXDs\ArcGIS_Layer_Files\Gregs_layer_files.gdb\sample_VRI_THLB_intersect_Ladybird 
bigCursor (inputFC, "THLB")                                     # FUNCTION_CALL
# bigCursor (inputFC, THLB_type):


