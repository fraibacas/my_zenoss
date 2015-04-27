#!/opt/zenoss/bin/python
import argparse
import pickle
import pymysql


HOST='localhost'
PORT=13306
USER='root'
PASSWORD=''
DB='zodb'


def parse_options():
    """Defines command-line options for script """
    parser = argparse.ArgumentParser(version="1.0",
                                     description="Sends radom requests to a solr instance to test performance.")
    parser.add_argument("-r", "--removed", action="store", default='/opt/zenoss/log/zodbpack_oids_to_remove.pickle', type=str,
                        help="Objects marked to be removed. list of oids")

    parser.add_argument("-p", "--pkes", action="store", nargs='+', default=[],
                        help="Objects marked to be removed. list of oids")

    return vars(parser.parse_args())

def check_if_pkes_were_packed(to_remove, pkes):
	print "Checking if pkes have ever been packed..."
	in_removed = [ oid for oid in pkes if int(oid) in to_remove ]
	print "\t{0} out of {1} oids had been marked for removal".format(len(in_removed), len(pkes))
	print "\t{0}".format(in_removed)

def check_who_references_pkes(pkes):
	print "Checking if pkes are referenced in the object_ref table..."
	with_refs = []
	conn = pymysql.connect(host=HOST, port=PORT, user=USER, passwd=PASSWORD, db=DB)
	cursor = conn.cursor()
	for oid in pkes:
		sql = """ SELECT zoid FROM {0} WHERE to_zoid={1} """.format('object_ref', oid)
		cursor.execute(sql)
		result = cursor.fetchall()
		if result:
			with_refs.append(oid)
			print '\tpke {0} is referenced from {1}'.format(oid, result[0][0])
	print "\tFound {0} pke oids out of {1} referenced in object_refs.".format(len(with_refs), len(pkes))


def main():
	cli_options = parse_options()
	if cli_options.get('removed') and cli_options.get('pkes'):
		pkes = cli_options.get('pkes')
		to_remove = []
		with open(cli_options.get('removed'), 'rb') as fp:
			removed = pickle.load(fp)
			for run, oids in removed.iteritems():
				for oid, tid in oids:
					to_remove.append(int(oid))
		check_if_pkes_were_packed(to_remove, pkes)
		check_who_references_pkes(pkes)

	else:
		print "ERROR: params needed"


if __name__ == '__main__':
	main()
