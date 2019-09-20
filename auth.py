from flask import Flask
from flask import jsonify
from flask import request
from flask_pymongo import PyMongo
from pymongo import MongoClient
import urllib
import redis
import json
from bson.objectid import ObjectId
import psutil
from kazoo.client import KazooClient

app = Flask(__name__)

# Intializing MongoDB Client ------------------------------------------------------------------------------
client = MongoClient("mongodb+srv://cubus:"+ urllib.quote_plus("@Cu2010bus") +"@cluster0-kxvpc.mongodb.net/test?retryWrites=true&w=majority")
mongodb = client.CubusDBTest

# Intializing Redis Client --------------------------------------------------------------------------------
redisdb = redis.Redis(host="redis-11737.c1.asia-northeast1-1.gce.cloud.redislabs.com",port="11737",password="vPt0IxefzMh8SdhfgbwzI5ltabzkz8BK")

# App route to validate the credentials -------------------------------------------------------------------
# Input Params : Username, Password
@app.route('/auth/validate/<userName>/<password>',methods=['POST'])
def userValidate(userName,password):
    redisdb.ping()
    users = mongodb.users
    result = []
    redisData = []
    user = users.find_one({'userName' : userName,'password':password})
    if user: 
        redisData = json.dumps({"result":{'id':str(user['_id']),'userId' : user['userId'],'firstName':user['firstName'], 'lastName':user['lastName'],'emailAddr':user['emailAddr']}})
        redisdb.setex(str(user['_id']),1800,redisData)
        result = {'id' : str(user['_id'])}
    else:
        result = {"ErrorDesc":"No Users Found"}
    return jsonify({'result':result})

# App route to get profile information ---------------------------------------------------------------------
# Input Params : ID
@app.route('/userprofile/userprofileget/<ID>',methods=['GET'])
def userProfileGet(ID):
    try:
        redisdb.ping()
        userInfo = redisdb.get(ID).decode('utf-8')
        redisdb.expire(ID,1800)
        return jsonify(userInfo)
    except Exception as ex:
        print("Error : "+ex)
        return("Failed to connect to redis")

# App route to update profile information -------------------------------------------------------------------
# Input Params : ID, FirstName, LastName, Email Address
@app.route('/userprofile/userprofileupdate/<Id>/<firstName>/<lastName>/<emailAddr>',methods=['POST'])
def userProfileUpdate(Id,firstName,lastName,emailAddr):
    try:
        users = mongodb.users
        query = {"_id":ObjectId(Id)}
        values = {"$set":{"firstName":firstName,"lastName":lastName,"emailAddr":emailAddr}}
        users.update_one(query,values)
        redisdb.ping()
        redisData = []
        redisData = json.dumps({"result":{'id':Id,'firstName':firstName, 'lastName':lastName,'emailAddr':emailAddr}})
        redisdb.setex(Id,1800,redisData)
        return json.dumps({"result":{"Success":"true"}})
    except Exception as ex:
        print("Error : " + ex)
        return("Failed to update profile information")

@app.route('/auth/healthcheck',methods=['GET'])
def getUsageParams():
    cpuPercent = psutil.cpu_percent(interval=None)
    totalMem = psutil.virtual_memory()[0]
    availMem = psutil.virtual_memory()[1]
    memPercent = psutil.virtual_memory()[2]
    diskPercent = psutil.disk_usage('/')[3]
    print("CPU Percentage : " + str(cpuPercent) + "%")
    print("Memory Percentage: " + str(memPercent) + "%")
    result = json.dumps({'result':{'cpuPercent':str(cpuPercent),'memPercent':str(memPercent),'diskPercent':str(diskPercent)}})
    # return(result)

zk = KazooClient(hosts='172.17.0.2:2181')
zk.start()
data = json.dumps({
        "authservice":{
            "url":"http://127.0.0.1:5000/auth/validate/"
            },
        "profileget":{
            "url":"http://127.0.0.1:5000/userprofile/userprofileget/"
        },
        "profileupdate":{
            "url":"http://127.0.0.1:5000/userprofile/userprofileupdate"
        },
        "healthcheck":{
            "url":"http://127.0.0.1:5000/auth/healthcheck"
        }
    })
if zk.exists("/jarvis/ironman"):
    print("Jarvis Updating Ironman")
    zk.set("/jarvis/ironman",data)
    print("Ironman Updated")
else:
    print("Jarvis Creating Ironman")
    zk.create("/jarvis/ironman",data)
    print("Ironman Created")
zk.stop()
if __name__ == '__main__':
    app.run(debug=True,host='127.0.0.1',port='5000')



