import pymongo

cli = pymongo.MongoClient().bilbil
collections = cli.list_collection_names()

for co_name in collections:
    if co_name == 'system.indexes':
        continue
    f = open('{}.json'.format(co_name), 'w')
    for i in cli[co_name].find():
        f.write(str(i))
    f.close()
    print('{}完成'.format(co_name))
