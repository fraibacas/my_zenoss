
from Products.Zuul.interfaces import ICatalogTool

# retrieves the names of the installed ZenPacks
#
zenpack_names = [ zp.id for zp in dmd.ZenPackManager.packs.objectValues() ]

# retrieves all the graph points
#
for gp in ICatalogTool(dmd).search('Products.ZenModel.GraphPoint.GraphPoint'):
    graph_point = gp.getObject()
    if 'pack' in graph_point.getRelationshipNames() and graph_point.pack() is not None:
        zp_name = graph_point.pack().id
        if zp_name not in zenpack_names:
            graph_point.pack.obj = None
            graph_point._p_changed = True

commit()
