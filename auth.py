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
import config
import logging
from flask import Response

app = Flask(__name__)

mongourl = ""
redishost=""
redisport=""
redispwd=""

# App route to validate the credentials -------------------------------------------------------------------
# Input Params : Username, Password
@app.route('/auth/validate/<userName>/<password>',methods=['POST'])
def userValidate(userName,password):
    print("Requested for username password validation")
    try:
        client = MongoClient(mongourl)
        mongodb = client.CubusDBTest

        redisdb = redis.Redis(host=redishost,port=redisport,password=redispwd)
        redisdb.ping()

        users = mongodb.users
        result = []
        redisData = []
        user = users.find_one({'userName' : userName,'password':password})
        if user: 
            redisData = json.dumps({"result":{'id':str(user['_id']),'userId' : user['userId'],'firstName':user['firstName'], 'lastName':user['lastName'],'emailAddr':user['emailAddr']}})
            redisdb.setex(str(user['_id']),1800,redisData)
            result = json.dumps({"result":{"status":"true","code":"200","data":{"id" : str(user['_id'])}}})
            result = Response(result,status=200,content_type="application/json")        
        else:
            result = jsonify({"result":{"status":"false","code":"500","reason":"No Users Found"}})
        print("Returning Response")
        client.close()
        return result
    except Exception as ex:
        result = jsonify({"result":{"status":"false","code":"500","reason":str(ex)}})
        return result

@app.route('/auth/healthz',methods=['GET'])
def getUsageParams():
    MongoOK = False
    RedisOK = False
    try:
        zk = KazooClient(hosts=config.ZOOKEEPER_HOST,timeout=5,max_retries=3)
        zk.start()
        print("ZOO Ok")
        zk.stop()

        client = MongoClient(mongourl)
        mongodb = client.CubusDBTest
        print("MongoDB Ok")
        MongoOK = True
        client.close()

        redisdb = redis.Redis(host=redishost,port=redisport,password=redispwd)
        print("MongoDB Ok")
        RedisOK = True

        jresp = json.dumps({"status":"OK","reason":"None"})
        resp = Response(jresp, status=200, mimetype='application/json')
        return resp

    except:
        Reason=None
        if MongoOK == False:
            print("Failed to connect to MongoDB")
            Reason = "Failed to connect to MongoDB"
        elif RedisOK == False:
            print("Failed to connect to RedisDB")
            Reason = "Failed to connect to RedisDB"
        else:
            print("Failed to connect to zoo keeper")
            Reason = "Failed to connect to zoo keeper"

        jresp = json.dumps({"status":"fail","reason":Reason})
        resp = Response(jresp, status=500, mimetype='application/json')
        return resp

if __name__ == '__main__':
    try:
        zk = KazooClient(hosts=config.ZOOKEEPER_HOST,timeout=5,max_retries=3)
        zk.start()
        try:
            if zk.exists("/databases/mongodb"):
                mongodata = zk.get("/databases/mongodb")
                mongodata = json.loads(mongodata[0])
                mongourl = mongodata["endpoints"]["url"]
                print("Fetched mongodb config from zookeeper")
            else:
                mongourl = config.MONGODB_HOST
        except:
            print("Failed to fetch mongodb config from zookeeper. Reverting to default value")
            mongourl = config.MONGODB_HOST
    
        try:
            if zk.exists("/databases/redisdb"):
                redisdata = zk.get("/databases/redisdb")
                redisdata = json.loads(redisdata[0])
                redishost = redisdata["endpoints"]["host"]
                redisport = redisdata["endpoints"]["port"]
                redispwd = redisdata["endpoints"]["password"]
                print("Fetched redisdb config from zookeeper")
            else:
                redishost = config.REDIS_HOST
                redisport = config.REDIS_PORT
                redispwd = config.REDIS_PASSWORD
        except:
            print("Failed to fetch redis config from zookeeper. Reverting to default value")
            redishost = config.REDIS_HOST
            redisport = config.REDIS_PORT
            redispwd = config.REDIS_PASSWORD
        
        data = json.dumps({
                "authservice":{
                    "url":"http://authservice.default.svc.cluster.local:4002/auth/validate/"
                },
                "healthcheck":{
                    "url":"http://authservice.default.svc.cluster.local:4002/auth/healthz"
                }
            })

        if zk.exists("/microservices/authservice"):
            print("Zookeeper Updating Authservice")
            zk.set("/microservices/authservice",data)
            print("Authservice configuration updated")
        else:
            print("Zookeeper Creating Authservice")
            zk.create("/microservices/authservice",data)
            print("Authservice configuration created")
        zk.stop()

    except:
        print("Failed to connect to zookeeper. Reverting to default value")
        redishost = config.REDIS_HOST
        redisport = config.REDIS_PORT
        redispwd = config.REDIS_PASSWORD

    app.run(debug=config.DEBUG_MODE,host='0.0.0.0',port=config.PORT)



