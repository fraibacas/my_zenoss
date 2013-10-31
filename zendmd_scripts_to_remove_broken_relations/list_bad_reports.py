""" Prints the reports that need to be fixed """
from Products.Zuul.interfaces import ICatalogTool

# retrieves the names of the installed ZenPacks
#
zenpack_names = [ zp.id for zp in dmd.ZenPackManager.packs.objectValues() ]

reports = {}

# retrieves all the graph points
#
for gp in ICatalogTool(dmd).search('Products.ZenModel.GraphPoint.GraphPoint'):
    graph_point = gp.getObject()
    if 'pack' in graph_point.getRelationshipNames() and graph_point.pack() is not None:
        zp_name = graph_point.pack().id
        if zp_name not in zenpack_names:
            report_name = graph_point.graphDef().report().id
            if report_name not in reports:
                reports[report_name] = True

print 'Reports to fix:\n{0}'.format('\n'.join(reports.keys()))