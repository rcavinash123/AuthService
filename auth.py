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

FORMAT = '%(asctime)-15s %(clientip)s %(user)-8s %(message)s'
logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)

app = Flask(__name__)

mongourl = ""
mongousername = ""
mongopassword = ""
redishost=""
redisport=""
redispwd=""

# App route to validate the credentials -------------------------------------------------------------------
# Input Params : Username, Password
@app.route('/auth/validate/<userName>/<password>',methods=['POST'])
def userValidate(userName,password):
    logging.debug("Requested for username password validation")
    try:
        client = MongoClient(mongourl,username=mongousername,password=mongopassword)
        mongodb = client.CubusDBTest

        redisdb = redis.Redis(host=redishost,port=redisport,password=redispwd)
        redisdb.ping()
        logging.debug("Before getting data from mongo db")
        users = mongodb.users
        result = []
        redisData = []
        user = users.find_one({'userName' : userName,'password':password})
        logging.debug("Got data from mongo db")
        if user: 
            redisData = json.dumps({"result":{'id':str(user['_id']),'userId' : user['userId'],'firstName':user['firstName'], 'lastName':user['lastName'],'emailAddr':user['emailAddr']}})
            redisdb.setex(str(user['_id']),1800,redisData)
            result = json.dumps({"result":{"status":"true","code":"200","data":{"id" : str(user['_id'])}}})
            result = Response(result,status=200,content_type="application/json")        
        else:
            result = json.dumps({"result":{"status":"false","code":"500","reason":"No Users Found"}})
        logging.debug("Returning Response")
        client.close()
        return result
    except Exception as ex:
        result = json.dumps({"result":{"status":"false","code":"500","reason":str(ex)}})
        return result

@app.route('/auth/healthz',methods=['GET'])
def getUsageParams():
    MongoOK = False
    RedisOK = False
    try:
        zk = KazooClient(hosts=config.ZOOKEEPER_HOST,timeout=5,max_retries=3)
        zk.start()
        logging.debug("ZOO Ok")
        zk.stop()

        client = MongoClient(mongourl,username=mongousername,password=mongopassword)
        mongodb = client.CubusDBTest
        logging.debug("MongoDB Ok")
        MongoOK = True
        client.close()

        redisdb = redis.Redis(host=redishost,port=redisport,password=redispwd)
        logging.debug("MongoDB Ok")
        RedisOK = True

        jresp = json.dumps({"status":"OK","reason":"None"})
        resp = Response(jresp, status=200, mimetype='application/json')
        return resp

    except:
        Reason=None
        if MongoOK == False:
            logging.debug("Failed to connect to MongoDB")
            Reason = "Failed to connect to MongoDB"
        elif RedisOK == False:
            logging.debug("Failed to connect to RedisDB")
            Reason = "Failed to connect to RedisDB"
        else:
            logging.debug("Failed to connect to zoo keeper")
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
                mongousername = mongodata["endpoints"]["username"]
                mongopassword = mongodata["endpoints"]["password"]
                logging.debug("Fetched mongodb config from zookeeper")
            else:
                mongourl = config.MONGODB_HOST
                mongousername = config.MONGODB_USERNAME
                mongopassword = config.MONGODB_PWD
        except:
            logging.debug("Failed to fetch mongodb config from zookeeper. Reverting to default value")
            mongourl = config.MONGODB_HOST
            mongousername = config.MONGODB_USERNAME
            mongopassword = config.MONGODB_PWD
    
        try:
            if zk.exists("/databases/redisdb"):
                redisdata = zk.get("/databases/redisdb")
                redisdata = json.loads(redisdata[0])
                redishost = redisdata["endpoints"]["host"]
                redisport = redisdata["endpoints"]["port"]
                redispwd = redisdata["endpoints"]["password"]
                logging.debug("Fetched redisdb config from zookeeper")
            else:
                redishost = config.REDIS_HOST
                redisport = config.REDIS_PORT
                redispwd = config.REDIS_PASSWORD
        except:
            logging.debug("Failed to fetch redis config from zookeeper. Reverting to default value")
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
            logging.debug("Zookeeper Updating Authservice")
            zk.set("/microservices/authservice",data)
            logging.debug("Authservice configuration updated")
        else:
            logging.debug("Zookeeper Creating Authservice")
            zk.create("/microservices/authservice",data)
            logging.debug("Authservice configuration created")
        zk.stop()

    except:
        logging.debug("Failed to connect to zookeeper. Reverting to default value")
        redishost = config.REDIS_HOST
        redisport = config.REDIS_PORT
        redispwd = config.REDIS_PASSWORD

    app.run(debug=config.DEBUG_MODE,host='0.0.0.0',port=config.PORT)



