# %%

import pyodbc as podbc
import urllib
from sqlalchemy import create_engine
import pandas as pd
import math
import numpy as np
import json

from flask import Flask, render_template, url_for, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


app = Flask(__name__)
conn = podbc.connect("Driver={SQL Server};Server=DESKTOP-FOBVP1N;Database=req_manager;uid=;pwd=")
params = urllib.parse.quote_plus("DRIVER={SQL Server};SERVER=DESKTOP-FOBVP1N;DATABASE=req_manager;uid=;pwd=")
app.config['SQLALCHEMY_DATABASE_URI'] = "mssql+pyodbc:///?odbc_connect=%s" % params
db = SQLAlchemy(app)

# updateResponse Function VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV
def updateResponse(clientId):
    latestSessionTableCal1 = pd.read_sql_query("SELECT * FROM Session_Table where C_ID = " + str(clientId) + "",conn)
    latestSessionTableCal2 = latestSessionTableCal1["Session_ID"]
    latestSessionID = latestSessionTableCal2.max()

    updatedSessionTable = pd.read_sql_query("SELECT * FROM Session_Table where C_ID = " + str(clientId) + " and Session_ID = " + str(latestSessionID) + "",conn)
    fieldTableLookup = pd.read_sql_query("SELECT * FROM Fields_Table",conn)
    fieldTableLookupMaxNumberCal1 = fieldTableLookup["F_ID"]
    fieldTableLookupMaxNumber = fieldTableLookupMaxNumberCal1.max()

    updated_session_field_join = pd.merge(updatedSessionTable, fieldTableLookup, on = 'F_ID')
    firstSessionTableRecord = updated_session_field_join.head(1)
    firstSessionTableRecordFormatCal = firstSessionTableRecord["Format"]
    firstSessionTableRecordFormatList = firstSessionTableRecordFormatCal.values.tolist()
    firstSessionTableRecordFormat = firstSessionTableRecordFormatList[0]
    firstSessionTableRecordBatchCal = firstSessionTableRecord["Batch"]
    firstSessionTableRecordBatchList = firstSessionTableRecordBatchCal.values.tolist()
    firstSessionTableRecordBatch = firstSessionTableRecordBatchList[0]
    response = ""
    if firstSessionTableRecordFormat == 2 and firstSessionTableRecordBatch == 1:
        #If XML-Batch is selected
        XMLBatchBeginning = '<Response xmlns="http://www.orchestra.com">\n<transactionDetails>\n<data fact="applicationId" value="elementValue"/>\n<data fact="transactionId" value="elementValue"/>\n</transactionDetails>\n'
        XMLBatchEnd = '</Response>'
        for i in range(fieldTableLookupMaxNumber):
            x = ""
            try: updated_session_field_join.iloc[[i]]
            except IndexError: x = None
            if x is None:
                pass
            else:
                row = updated_session_field_join.iloc[[i]]
                xmlBatchValue = row["XML_Batch"]
                xmlBatchValueList = xmlBatchValue.values.tolist()
                xmlBatchValueFirst = xmlBatchValueList[0]
                response = response + xmlBatchValueFirst + '\n'

        finalResponse = XMLBatchBeginning + response + XMLBatchEnd
        finalResponseStr = str(finalResponse[0])
        query2 = "UPDATE [dbo].[Client_Table] SET [Response] = " + "'" + finalResponse + "'" + " WHERE [C_ID] = " + str(clientId) + ""
        cursor = conn.cursor()
        cursor.execute(query2)
        cursor.commit()

    elif firstSessionTableRecordFormat == 1 and firstSessionTableRecordBatch == 0:
        #If JSON is selected
        def thirdSectionConstruction(thirdSection):
            JSONColumn3 = pd.DataFrame(updated_session_field_join,columns=['JSON','F_Sub2Category','F_Sub1Category','F_Category'])
            thirdSectionResponseCal = ""
            for i in range(len(JSONColumn3)):
                if JSONColumn3.F_Sub2Category[i] == thirdSection:
                    currentResponseField = JSONColumn3.JSON[i]
                    thirdSectionResponseCal = thirdSectionResponseCal + currentResponseField + " " + '\n'
                else:
                    pass
            thirdSectionResponseCal = '"' + thirdSection + '":' + ' {' + '\n' + thirdSectionResponseCal[:-3] + '\n' + "},"
            return thirdSectionResponseCal


        def secondSectionConstruction(secondSection):
            JSONColumn2 = pd.DataFrame(updated_session_field_join,columns=['F_Sub2Category','F_Sub1Category','F_Category'])
            JSONColumn2Filtered = JSONColumn2.loc[(JSONColumn2.F_Sub1Category == secondSection)]
            JSONColumn2_1 = pd.DataFrame(JSONColumn2Filtered,columns=['F_Sub2Category'])
            JSONColumn2_1List = JSONColumn2_1.values.tolist()
            JSONColumn2_1ListNumpy = np.array(JSONColumn2_1List)
            JSONColumn2_1ListUniqueValues = np.unique(JSONColumn2_1ListNumpy)
            secondSectionResponseCal = ""
            for x in range(len(JSONColumn2_1ListUniqueValues)):
                    thirdSection = JSONColumn2_1ListUniqueValues[x]
                    thirdSectionResponse = thirdSectionConstruction(thirdSection)
                    secondSectionResponseCal = secondSectionResponseCal + '\n' + thirdSectionResponse
            secondSectionResponseCal = '"' + secondSection + '":' + ' {' + secondSectionResponseCal[:-1] + '\n' + "},"
            return secondSectionResponseCal


        def firstSectionConstruction(firstSection):
            JSONColumn1_1 = pd.DataFrame(updated_session_field_join,columns=['F_Sub1Category', 'F_Category'])
            JSONColumn1_1Filtered = JSONColumn1_1.loc[(JSONColumn1_1.F_Category == firstSection)]
            JSONColumn1_1List = JSONColumn1_1Filtered.values.tolist()
            JSONColumn1_1ListNumpy = np.array(JSONColumn1_1List)
            JSONColumn1_1ListUniqueValues = np.unique(JSONColumn1_1ListNumpy[:,0])
            firstSectionResponseCal = ""
            for x in range(len(JSONColumn1_1ListUniqueValues)):
                    secondSection = JSONColumn1_1ListUniqueValues[x]
                    secondSectionResponse = secondSectionConstruction(secondSection)
                    firstSectionResponseCal = firstSectionResponseCal + '\n' + secondSectionResponse
            firstSectionResponseCal = '"' + firstSection + '":' + ' {' + firstSectionResponseCal[:-1] + '\n' + "},"
            return firstSectionResponseCal


        JSONCategories = pd.DataFrame(updated_session_field_join,columns=['F_Category'])
        JSONCategoriesList = JSONCategories.values.tolist()
        JSONCategoriesListNumpy = np.array(JSONCategoriesList)
        JSONCategoriesListUniqueValues = np.unique(JSONCategoriesListNumpy)

        fullResponseCal = ""
        for x in range(len(JSONCategoriesListUniqueValues)):
            firstSection = JSONCategoriesListUniqueValues[x]
            firstSectionResponse = firstSectionConstruction(firstSection)
            fullResponseCal = fullResponseCal + '\n' + firstSectionResponse
        fullResponse = '{"SphonicResponse":{\n"data":{' + fullResponseCal[:-1] + '\n' + "}}}"
        fullResponseBeautifyCal = json.loads(fullResponse)
        fullResponseBeautify = json.dumps(fullResponseBeautifyCal, indent=2)
        finalResponse = fullResponseBeautify
        query2 = "UPDATE [dbo].[Client_Table] SET [Response] = " + "'" + finalResponse + "'" + " WHERE [C_ID] = " + str(clientId) + ""
        cursor = conn.cursor()
        cursor.execute(query2)
        cursor.commit()

    elif firstSessionTableRecordFormat == 1 and firstSessionTableRecordBatch == 1:
        #If JSON-Batch is selected
        JSONBatchBeginning = '{"SphonicResponse":\n'
        for i in range(fieldTableLookupMaxNumber):
            x = ""
            try: updated_session_field_join.iloc[[i]]
            except IndexError: x = None
            if x is None:
                pass
            else:
                row = updated_session_field_join.iloc[[i]]
                JSONBatchValue = row["JSON_Batch"]
                JSONBatchValueList = JSONBatchValue.values.tolist()
                JSONBatchValueFirst = JSONBatchValueList[0]
                response = response + JSONBatchValueFirst + '\n'

        finalResponse = JSONBatchBeginning + response[:-2] + '\n}'
        finalResponseStr = str(finalResponse[0])
        query2 = "UPDATE [dbo].[Client_Table] SET [Response] = " + "'" + finalResponse + "'" + " WHERE [C_ID] = " + str(clientId) + ""
        cursor = conn.cursor()
        cursor.execute(query2)
        cursor.commit()

    elif firstSessionTableRecordFormat == 2 and firstSessionTableRecordBatch == 0:
        #If XML is selected
        XMLBeginning = '<Response xmlns="http://www.orchestra.com">\n<transactionDetails>\n<data fact="applicationId" value="elementValue"/>\n<data fact="transactionId" value="elementValue"/>\n</transactionDetails>\n'
        XMLEnd = '</Response>'
        for i in range(fieldTableLookupMaxNumber):
            x = ""
            try: updated_session_field_join.iloc[[i]]
            except IndexError: x = None
            if x is None:
                pass
            else:
                row = updated_session_field_join.iloc[[i]]
                xmlValue = row["XML"]
                xmlValueList = xmlValue.values.tolist()
                xmlValueFirst = xmlValueList[0]
                response = response + xmlValueFirst + '\n'

        finalResponse = XMLBeginning + response + XMLEnd
        finalResponseStr = str(finalResponse[0])
        query2 = "UPDATE [dbo].[Client_Table] SET [Response] = " + "'" + finalResponse + "'" + " WHERE [C_ID] = " + str(clientId) + ""
        cursor = conn.cursor()
        cursor.execute(query2)
        cursor.commit()

    else:
        finalResponse = ""
        query2 = "UPDATE [dbo].[Client_Table] SET [Response] = " + "'" + finalResponse + "'" + " WHERE [C_ID] = " + str(clientId) + ""
        cursor = conn.cursor()
        cursor.execute(query2)
        cursor.commit()
# updateResponse Function ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


# Index Logic and Page VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV

@app.route('/', methods=['POST', 'GET'])
def index():
        clientTableIndex = pd.read_sql_query("SELECT * FROM Client_Table",conn)
        clientNameIndex = clientTableIndex["Client_Name"]
        clientNames = clientNameIndex.values.tolist()
        clientIdIndex = clientTableIndex["C_ID"]
        clientIds = clientIdIndex.values.tolist()
        clientStatusIndex = clientTableIndex["Client_Status"]
        clientStatus = clientStatusIndex.values.tolist()
        clientDetails = zip(clientNames, clientStatus, clientIds) 
        return render_template('index.html', clientDetails=clientDetails,)

# Index Logic and Page ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



# Client Page VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV

@app.route('/client/<int:clientId>', methods=['POST', 'GET'])
def client(clientId):

    clientTable = pd.read_sql_query("SELECT * FROM Client_Table where C_ID = " + str(clientId) + "",conn)

    clientNameColumn = clientTable["Client_Name"]
    clientNameList = clientNameColumn.values.tolist()
    clientName = clientNameList[0]

    
    clientStatusColumn = clientTable["Client_Status"]
    clientStatusList = clientStatusColumn.values.tolist()
    clientStatus = clientStatusList[0]

    pManagerColumn = clientTable["P_Manager"]
    pManagerList = pManagerColumn.values.tolist()
    pManager = pManagerList[0]

    sManagerColumn = clientTable["S_Manager"]
    sManagerList = sManagerColumn.values.tolist()
    sManager = sManagerList[0]

    clientTableColumn = clientTable["Response"]
    clientTableList = clientTableColumn.values.tolist()
    clientResponse = clientTableList[0]
    clientResponse = clientResponse.replace('> <', '<\n>')

    latestSessionTableCal1 = pd.read_sql_query("SELECT * FROM Session_Table where C_ID = " + str(clientId) + "",conn)
    latestSessionTableCal2 = latestSessionTableCal1["Session_ID"]
    latestSessionID = latestSessionTableCal2.max()

    if latestSessionTableCal1.empty != True:
        latestSessionTable = pd.read_sql_query("SELECT * FROM Session_Table where C_ID = " + str(clientId) + " and Session_ID = " + str(latestSessionID) + "",conn)
        fieldTable = pd.read_sql_query("SELECT * FROM Fields_Table",conn)
        session_field_join = pd.merge(latestSessionTable, fieldTable, on = 'F_ID')
        if session_field_join.empty:
            pass
        else:
            fields_List = session_field_join["Field"]
            fields_List2 = session_field_join.values.tolist()
        allFields1 = fieldTable.values.tolist()
        allFields = allFields1
        selectedfields = fields_List2
    else:
        fieldTable = pd.read_sql_query("SELECT * FROM Fields_Table",conn)
        allFields1 = fieldTable.values.tolist()
        allFields = allFields1
        selectedfields = ""

    numberOFCategoriesCal = fieldTable.values.tolist()
    numberOFCategoriesNumpy = np.array(numberOFCategoriesCal)
    numberOFCategories = np.unique(numberOFCategoriesNumpy[:,2])

    clientIdRequirements = clientId
    return render_template('client.html', clientResponse=clientResponse, selectedfields=selectedfields, fields=allFields, clientId=clientIdRequirements, numberOFCategories=numberOFCategories, clientName=clientName, pManager=pManager, sManager=sManager, clientStatus=clientStatus)

# Requirements Gathering Logic VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV

@app.route('/requirements/<int:clientId>', methods=['POST', 'GET'])
def requirements(clientId):
    if request.method == 'POST':

        clientSessionIds = pd.read_sql_query("SELECT * FROM Session_Table where C_ID = " + str(clientId) + "",conn)
        allSessionIds = clientSessionIds["Session_ID"]
        previousSessionId = allSessionIds.max()
        latestSessionIdQuery = previousSessionId + 1
        latestSessionIdQueryIsNan = math.isnan(latestSessionIdQuery)

        #If this is a newly created client, assign its session ID to 0
        if latestSessionIdQueryIsNan == True:
            latestSessionIdQuery = 0
        else:
            latestSessionIdQuery = latestSessionIdQuery

        
        #Checks if batch has been selected or not
        formatEmpty = "Not Empty"
        try: request.form['Format']
        except KeyError: formatEmpty = None
        if formatEmpty is None:
            #JSON is selected
            formatSelected = "1"
        else:
            #XML is selected
            formatSelected = "2"
        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

        #Checks if batch has been selected or not
        batchEmpty = "Not Empty"
        try: request.form['Batch']
        except KeyError: batchEmpty = None
        if batchEmpty is None:
            #Batch is not selected
            batchSelected = "0"
        else:
            #Batch is selected
            batchSelected = "1"
        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

        fieldTableMaxNumberCal1 = pd.read_sql_query("SELECT * FROM Fields_Table",conn)
        fieldTableMaxNumberCal2 = fieldTableMaxNumberCal1["F_ID"]
        fieldTableMaxNumber = fieldTableMaxNumberCal2.max()

        #Goes through all selected requirements and adds it to the session table
        for i in range(fieldTableMaxNumber):
            x = ""
            iStr = str(i)
            try: request.form[iStr]
            except IndexError: x = None
            except NameError: x = None
            except KeyError: x = None
            if x is None:
                x = None
            else:
                y = request.form[iStr]
                y = str(y)
                query = "INSERT INTO [dbo].[Session_Table]([F_ID],[Session_ID],[C_ID],[Format],[Batch]) VALUES(" + str(y) + "," + str(latestSessionIdQuery) + ", " + str(clientId) + ", " + formatSelected + ", " + batchSelected + ")"
                cursor = conn.cursor()
                cursor.execute(query)
                cursor.commit()
        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

        #Concatenates all fields together
        updateResponse(clientId)
        #Concatenates all fields together

        return redirect(url_for('client', clientId=clientId))

    else: 
        return redirect(url_for('client', clientId=clientId))

# Requirements Gathering Logic ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

# Client Page ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


# Delete Logic VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV

@app.route('/delete/<int:F_ID>/<int:clientId>')
def delete(F_ID, clientId):
    latestSessionTableCal1 = pd.read_sql_query("SELECT * FROM Session_Table where C_ID = " + str(clientId) + "",conn)
    latestSessionTableCal2 = latestSessionTableCal1["Session_ID"]
    latestSessionID = latestSessionTableCal2.max()

    deleteQuery = "DELETE FROM [dbo].[Session_Table] WHERE F_ID = " + str(F_ID) + "and Session_ID = " + str(latestSessionID) 
    cursor = conn.cursor()
    cursor.execute(deleteQuery)
    cursor.commit()

    updateResponse(clientId)

    return redirect(url_for('client', clientId=clientId))

# Delete Logic ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


# NewClient Logic VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV

@app.route('/NewClient')
def NewClient():
    return render_template('newClient.html')

# NewClient Logic ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

# AddNewClient Logic VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV

@app.route('/AddNewClient', methods=['POST'])
def AddNewClient():
    clientName = request.form['clientName']
    clientStatus = request.form['clientStatus']
    PTechnicalManager = request.form['PTechnicalManager']
    STechnicalManager = request.form['STechnicalManager']
    query = "INSERT INTO [dbo].[Client_Table]([Client_Name],[Client_Status],[P_Manager],[S_Manager],[Response]) VALUES(" + "'" + clientName + "'" + ", " + "'" + clientStatus + "'" + ", " + "'" + PTechnicalManager + "'" + ", " + "'" + STechnicalManager + "'" + ", " "'" + " " + "'" +  ")"
    cursor = conn.cursor()
    cursor.execute(query)
    cursor.commit()
    return redirect('/')

# AddNewClient Logic ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


# Settings Logic VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV

@app.route('/Settings/<int:clientId>')
def Settings(clientId):
    clientTable = pd.read_sql_query("SELECT * FROM Client_Table where C_ID = " + str(clientId) + "",conn)

    clientNameColumn = clientTable["Client_Name"]
    clientNameList = clientNameColumn.values.tolist()
    clientName = clientNameList[0]

    clientStatusColumn = clientTable["Client_Status"]
    clientStatusList = clientStatusColumn.values.tolist()
    clientStatus = clientStatusList[0]

    pManagerColumn = clientTable["P_Manager"]
    pManagerList = pManagerColumn.values.tolist()
    pManager = pManagerList[0]

    sManagerColumn = clientTable["S_Manager"]
    sManagerList = sManagerColumn.values.tolist()
    sManager = sManagerList[0]

    clientId = clientId

    return render_template('updateClient.html', clientName=clientName, pManager=pManager, sManager=sManager, clientStatus=clientStatus, clientId=clientId)

# Settings Logic ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


# updateClient Logic VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV

@app.route('/UpdateClient/<int:clientId>', methods=['POST'])
def UpdateClient(clientId):
    clientName = request.form['clientName']
    clientStatus = request.form['clientStatus']
    PTechnicalManager = request.form['PTechnicalManager']
    STechnicalManager = request.form['STechnicalManager']
    query = "UPDATE [dbo].[Client_Table] SET [Client_Name] = " + "'" + clientName + "',[Client_Status] = '" + clientStatus + "',[P_Manager] = '" + PTechnicalManager + "',[S_Manager] = '" + STechnicalManager + "' WHERE [C_ID] = " + str(clientId) + ""
    cursor = conn.cursor()
    cursor.execute(query)
    cursor.commit()
    clientId = clientId
    return redirect('/client/' + str(clientId))

# updateClient Logic ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


# Delete Client Logic VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV

@app.route('/deleteClient/<int:clientId>')
def deleteClient(clientId):
    deleteQuery = "DELETE FROM [dbo].[Client_Table] WHERE C_ID = " + str(clientId)
    cursor = conn.cursor()
    cursor.execute(deleteQuery)
    cursor.commit()
    return redirect('/')

# Delete Client Logic ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

if __name__ == "__main__":
    app.run(debug=True)
# %%
