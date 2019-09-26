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
mongodb_ok = False
redis_ok = False


# App route to validate the credentials -------------------------------------------------------------------
# Input Params : Username, Password
@app.route('/auth/validate/<userName>/<password>',methods=['POST'])
def userValidate(userName,password):
    print("Requested for username password validation")
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
    print("Returning Response")
    return jsonify({'result':result})

@app.route('/auth/healthz',methods=['GET'])
def getUsageParams():
    try:
        zk = KazooClient(hosts=config.ZOOKEEPER_HOST,timeout=5,max_retries=3)
        zk.start()
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
            zk.stop()
            print("Authservice configuration updated")
        else:
            print("Zookeeper Creating Authservice")
            zk.create("/microservices/authservice",data)
            print("Authservice configuration created")
            zk.stop()
        if mongodb_ok == True and redis_ok == True:
            print("Connectivity to the zoo keeper succeeded")
            jresp = json.dumps({"status":"success","reason":"none"})
            resp = Response(jresp, status=200, mimetype='application/json')
            zk.stop()
            return resp
        else:
            print("Failed to connect to mongodb or redis")
            jresp = json.dumps({"status":"fail","reason":"Failed to connect to mongo/redis"})
            resp = Response(jresp, status=500, mimetype='application/json')
            zk.stop()
            return resp
    except:
        print("Failed to connect to zoo keeper")
        jresp = json.dumps({"status":"fail","reason":"Failed to connect to zookeeper"})
        resp = Response(jresp, status=500, mimetype='application/json')
        return resp

    

if __name__ == '__main__':
    # Intializing MongoDB Client ------------------------------------------------------------------------------
    try:
        client = MongoClient(config.MONGODB_HOST)
        mongodb = client.CubusDBTest
        mongodb_ok = True
        print("Mongo DB OK")
    except Exception as ex:
        print("Exception occured while connecting to mongo db error : " + str(ex))

# Intializing Redis Client --------------------------------------------------------------------------------
    try:
        redisdb = redis.Redis(host=config.REDIS_HOST,port=config.REDIS_PORT,password=config.REDIS_PASSWORD)
        redis_ok = True
        print("Redis OK")
    except Exception as ex:
        print("Exception occured while connecting to redis db : " + str(ex))
    app.run(debug=config.DEBUG_MODE,host='0.0.0.0',port=config.PORT)



