import mysql.connector
import csv
import gspread
import time
from decimal import *
#make sure to install gspread and connector with python pip

#mySQL connection
myDB = mysql.connector.connect(
  host="localhost",
  user="root",
  password="Enter your password here"
)

#list that hold different transaction data
transactions = [] #list of lists
myCategories = ["Food", "Subscriptions", "Financial Services", "Utilities"]
food = ["DD BR", "JERSEY MIKES"]
subscriptions = ["CHEGG", "TESLA SUBSCRIPTION", "SPOTIFY"]
utilities = ["TESLA SUPERCHARGER", "BFS FOODS"]
financialServices = ["Zelle", "Cash App", "Venmo"]
columnFormat = "{:^12}{:^50}{:^20}{:^12}"


def dbExists():
    checkCursor = myDB.cursor()
    result = checkCursor.execute("SHOW DATABASES LIKE 'myFinances'")
    if result:
        return True
    return False

#formats dates for mySQL
def dateFormatter(dateString):
    dateList = dateString.split("/")
    newDate = f"20{dateList[2]}/{dateList[0]}/{dateList[1]}"
    #print("new date: " + newDate)
    return newDate

#checks if a category value is part of a description
def inList(categoryList,description):
    for element in categoryList:
        if element in description:
            return True
    
    return False

#decides what category a transaction falls into
def findCategory(description):

    if inList(food, description):
        return "Food"
    elif inList(subscriptions, description):
        return "Subscriptions"
    elif inList(utilities, description):
        return "Utilities"
    elif inList(financialServices, description):
        return "Financial Services"
    else:
        return "N/A"

#formats each transaction/row retrieved from db and prints it out
def formatQueryResult(resultTuple):
    date = resultTuple[0].strftime('%Y/%m/%d')
    description = resultTuple[1].strip()
    category = resultTuple[2].strip()
    amount = resultTuple[3]

    #print(date, description, type, amount)
    print(columnFormat.format(date,description,category,amount))

def retrieveAllTransactions():
    if dbExists == False:
        print("DB empty, please import transactions.")
        return

    queryResult = list()
    myCursor = myDB.cursor()
    myDB.database = "myFinances"
    myCursor.execute("SELECT * FROM transactions")
    
    print(columnFormat.format("Date:", "Description:", "Category:","Amount:"))
    for transaction in myCursor:
        formatQueryResult(transaction)
        
    
  

#opens cvs file and creates a list of transactions (list of lists)
def createTransactions(file):
    #transactions = list()
    with open(file, mode = 'r') as csv_file:
        csvReader = csv.reader(csv_file)
        for i,row in enumerate(csvReader):
            #skip row that contains column names
            if i == 0:
                continue
           
            date = dateFormatter(row[2])
            if "-" in row[1]:
                description = (row[1].split("-")[1]).strip()
            else:
                description = row[1].strip()

            if "Deposit" not in description and "received" not in description and "Interest Paid" not in description:
                amount = -float(row[4])
                
            else:
                amount = float(row[4])

            category = findCategory(description)
            
            transaction = (date, description, category, amount)
            transactions.append(transaction)

    return transactions          

#saves current transaction list to database
#if 1st time, creates database and table for you
def saveToDB():
    myCursor = myDB.cursor()
    myCursor.execute("CREATE DATABASE IF NOT EXISTS myFinances")
    myDB.database = "myFinances"
    myCursor.execute("""CREATE TABLE IF NOT EXISTS transactions 
    (transaction_date DATE, 
    description VARCHAR(500), 
    category VARCHAR(50), 
    amount DECIMAL(13,2))""")

    # myCursor.execute("SHOW DATABASES")
    # for x in myCursor:
    #     print(x)
    
    count = 0
    sql = "INSERT INTO transactions ( transaction_date, description, category, amount) VALUES (%s,%s,%s,%s)"
    for transaction in transactions:
        myCursor.execute(sql, (transaction[0], transaction[1], transaction[2], transaction[3]))
        count = count + 1
    
    if count > 0:
        print(f"{count} transactions added.")
    else:
        print("Database is up to date.")

    myDB.commit()
    
      

def sendToGoogleSheets(month):
    #open google sheet and insert data
    sa = gspread.service_account()
    sh = sa.open("Finances")
    wks = sh.worksheet(f"{month}")
    print("Sending transactions over......")
    #each col corresponds to a transaction field
    for row in transactions:
        wks.insert_row([row[0], row[1], row[2], row[3]], 8)
        #in compliance with API
        time.sleep(2)

    print("Complete")

#finds category count for all transactions
def findCounts():
    #each element will be an innerlist of the category count and category index in myCategories list
    categoryCounts = []
    myDB.database = "myFinances"
    myCursor = myDB.cursor()

    for i, category in enumerate(myCategories):
        myCursor.execute(f"SELECT count(category) from transactions where category = '{category}'")
        #query returns tuple
        categoryCounts.append([myCursor.fetchone()[0], i]) 
      
    
    return categoryCounts



#displays purchases by category, most occuring purchase, total amounts
def displayStats():
    if dbExists == False:
        print("DB empty, please import transactions.")
        return

    myDB.database = "myFinances"
    myCursor = myDB.cursor()
    
    categoryAmounts = findCounts()
    myAmounts = []
    for list in categoryAmounts:
        myAmounts.append(list[0])

    print(f"-Finance Statistics-\n")
    print("Purchase occurrences by Category:")

    myAmounts.sort(reverse = True)
    for amount in myAmounts:
        for inList in categoryAmounts:
            if(amount == inList[0]):
                i = inList[1]
                print(f"{myCategories[i]}: {inList[0]}")
                break
        

    #find most common transaction
    myCursor.execute("SELECT description, COUNT(description) as occurrence FROM transactions GROUP BY description ORDER BY occurrence DESC")
    result = myCursor.fetchone()
    purchase = result[0]
    occurr = result[1]
    print(f"\nMost common purchase:\n{purchase} - {occurr} times!\n")
    myCursor.reset()
    myCursor.execute("SELECT sum(amount) FROM transactions WHERE amount < 0")
    purchaseTotal = myCursor.fetchone()[0] * -1
    myCursor.execute("SELECT sum(amount) FROM transactions WHERE amount > 0")
    earnings = myCursor.fetchone()[0] 
    myCursor.execute("SELECT sum(amount) FROM transactions")
    moneySaved = myCursor.fetchone()[0] 
    
    print(f"Total earnings: {earnings}")
    print(f"Money spent: ${purchaseTotal}")
    print(f"Savings: ${moneySaved}\n")
    
   
def displayMenu():
    print("1 - View all your transactions")
    print("2 - Transaction Statistics")
    print("3 - Import bank transactions")
    print("4 - Save to Database")
    print("5 - Exit")
    menuChoice = int(input(">"))
    return menuChoice

def printList(list):
    for i, element in enumerate(list):
        print(f"{i}: {element}")
    
    
if __name__ == "__main__":
    print(f"Welcome back \nEnter an option:\n")
    
    while True:
        menuChoice = displayMenu()

        if menuChoice == 1:
            retrieveAllTransactions()

        if menuChoice == 2:
            displayStats()

        if(menuChoice == 3):
            print("in 3")
            #grabs month of file
            print("Enter the month of the file you want to import")
            month = input(">")
            file = f"C1_{month}.csv"
            transactions = createTransactions(file)
            printList(transactions)

            print("Would you like to send data to Google Sheets? (y/n)")
            response = input(">").lower()
            if response == "y":
                sendToGoogleSheets(month)

        if menuChoice == 4:
            saveToDB()
        
            
        if menuChoice == 5:
            break



    

            
        

            

        




