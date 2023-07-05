from web3 import Web3
import json
import datetime
import psycopg2
import schedule
import time
import csv
import base64
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (Mail, Attachment, FileContent, FileName, FileType, Disposition)
from google.cloud import secretmanager

def getSecret(name):
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(name=name)
    return response.payload.data.decode('UTF-8')

'''
Fetch secret values
'''
sqlPwdName = os.environ["GCP_SECRET_MGR_SQL_PRIVATE_KEY"]
sqlPwd = getSecret(sqlPwdName)
infuraApiName = os.environ["GCP_SECRET_MGR_INFURA_API_KEY"]
infuraApi = getSecret(infuraApiName)
sendgridApiName = os.environ["GCP_SECRET_MGR_SENDGRID_API_KEY"]
sendgridApi = getSecret(sendgridApiName)

'''
Connect to provider
'''
w3 = Web3(Web3.HTTPProvider(f"https://mainnet.infura.io/v3/{infuraApi}"))

'''
Make an instance of a contract
'''
# NFTAddr = "0x8915571F2828e692BAFA0D6dE5C4667d095695bB" # mumba
# NFTAddr = "0x1266ecdbbff533b0dbf885043f704bcf2737a3aa" # mainnet
NFTAddr = "0xd774557b647330C91Bf44cfEAB205095f7E6c367" # testing
if(os.environ.get("NFT_ADDRESS")):
    NFTAddr = os.environ["NFT_ADDRESS"]
f = open('abi/MetaDuetNFTv2.json')
abi = f.read()
NFT = w3.eth.contract(abi=abi, address=w3.toChecksumAddress(NFTAddr))

'''
Reads processing status from blockNumber.txt. Then parse and stores events to db.
'''
def getOrders():

    print("getting order")
    # load progress status from file
    f = open("blockNumber.txt", 'r')
    fromBlock = int(f.read())
    f.close()
    latestBlock = w3.eth.get_block_number()

    # prepare for db
    # make sure the connection to db is authorized
    print("connecting db")
    conn = psycopg2.connect(
        host="34.81.21.99",
        database="postgres",
        user="yen.liao@taisys.com",
        password=sqlPwd
    )
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS NFT (orderNumber VARCHAR(50) PRIMARY KEY, date TIMESTAMP NOT NULL, product VARCHAR(50) NOT NULL, amount INTEGER NOT NULL, tokenId INTEGER NOT NULL UNIQUE, price REAL NOT NULL, total_price REAL NOT NULL)")

    # read and store events
    cachedBlockNumbers = {}
    toBlock = latestBlock
    while(fromBlock < latestBlock):
        print(f"from {fromBlock} to {toBlock}")
        try:
            data = []
            # get all mint events in the range
            mintEvents = NFT.events.Transfer().createFilter(
                fromBlock=fromBlock,
                toBlock=toBlock,
                argument_filters={'from':"0x0000000000000000000000000000000000000000"}
            ).get_all_entries()
            print(f"got {len(mintEvents)}")
            for event in mintEvents:
                if(not cachedBlockNumbers.get(event.blockNumber)):
                    cachedBlockNumbers[event.blockNumber] = w3.eth.get_block(event.blockNumber).timestamp
                ts = datetime.date.fromtimestamp(cachedBlockNumbers[event.blockNumber])
                data.append(
                    (
                        "MD-{}{}{}{}".format(
                            ts.year,
                            str(ts.month).zfill(2),
                            str(ts.day).zfill(2),
                            str(event.args.tokenId).zfill(7)
                        ),
                        ts,
                        "MetaDuet Card",
                        1,
                        event.args.tokenId,
                        0.45,
                        0.45
                    )
                )
            for d in data:
                cursor.execute(
                    "INSERT INTO NFT (orderNumber, date, product, amount, tokenId, price, total_price) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                    ,d)
            fromBlock = toBlock + 1
            toBlock = latestBlock
        except KeyboardInterrupt:
            sys.exit()
        except:
            # read half of blocks when event filter too big
            toBlock = ((toBlock - fromBlock) // 2) + fromBlock
    conn.commit()
    cursor.close()

    # send mail if it's the first day of every month
    today = datetime.date.today()
    if(True):
        f = open("config.json", 'r')
        config = json.load(f)
        f.close()

        # filter data from db
        query = """SELECT * FROM NFT WHERE DATE >= %s AND DATE < %s;"""
        cursor = conn.cursor()
        if(today.month == 1):
            lastMonth = datetime.date(today.year-1, 12, 1)
        else:
            lastMonth = datetime.date(today.year, today.month-1, 1)
        cursor.execute(query, (lastMonth, today))
        rows = cursor.fetchall()
        with open("output.csv", "w", newline = "") as csv_file:
            csv_writer = csv.writer(csv_file)
            column_names = [desc[0] for desc in cursor.description]
            csv_writer.writerow(column_names)

            for row in rows:
                csv_writer.writerow(row)

        # Prepare email
        message = Mail(
            from_email =config["sender"],
            to_emails=config["receivers"],
            subject=f"MetaDuet EA {datetime.date.today()} report",
            html_content = "<strong>Machine generated email, please do not reply</strong>"
        )
        with open("output.csv", "rb") as f:
            data = f.read()
            encoded_file = base64.b64encode(data).decode()
            attachedFile = Attachment(
                FileContent(encoded_file),
                FileName('report.csv'),
                FileType('application/csv'),
                Disposition('attachment')
            )
            message.attachment = attachedFile
        try:
            sg = SendGridAPIClient(sendgridApi)
            response = sg.send(message)
            print("mail sent")
        except Exception as e:
            print(e)

    # store progress status to file
    f = open("blockNumber.txt", 'w')
    f.write(str(latestBlock))
    f.close()
    print(datetime.datetime.now())

    conn.close()

# Schedule getOreders call periodically
schedule.clear()
schedule.every(float(os.environ["PERIOD_IN_HOUR"])).hours.do(getOrders)

# Keep the script running continuously
while True:
    schedule.run_pending()
    time.sleep(3)

# getOrders()
