def buildGeometryFromDict(innerBuildDict, outerBuildDict, innerRadialBuildStart, outerRadialBuildStart, height):
    #build dict {'layer_name' : {'thickness': float, 'material': openmc material}}
    #define surfaces
    top = openmc.ZPlane(z0=height/2, boundary_type='periodic', surface_id = 10001)
    bottom = openmc.ZPlane(z0=-height/2, boundary_type='periodic', surface_id=10002)

    #build the inboard side surfaces
    innerSurfaces = {}
    offset = innerRadialBuildStart
    for key, value in innerBuildDict.items():
        innerSurfaces[key] = openmc.ZCylinder(r=offset)
        offset -= value['thickness']

    innermostSurface = openmc.ZCylinder(r=offset)

    #build the inboard side regions
    innerRegions = {}
    surfList = list(innerSurfaces.keys())
    for i in range(len(surfList)):
        if i != len(surfList)-1:
            innerRegions[surfList[i]] = -top & +bottom & -innerSurfaces[surfList[i]] & +innerSurfaces[surfList[i+1]]
        else:
            innerRegions[surfList[i]] = -top & +bottom & -innerSurfaces[surfList[i]] & +innermostSurface

    centralVoid = -innermostSurface & +bottom & -top

    #build the inboard side cells
    innerCells = {}
    for key, value in innerBuildDict.items():
        if value['material'] == 'vacuum':
            innerCells[key] = openmc.Cell(region=innerRegions[key], name = key + ' inner',cell_id=innerBuildDict[key]['cell_id'])
        else:
            innerCells[key] = openmc.Cell(region=innerRegions[key], name = key + ' inner', fill = innerBuildDict[key]['material'],cell_id=innerBuildDict[key]['cell_id'])

    innerCells['central_void'] = openmc.Cell(region=centralVoid,cell_id=10000, name='central void')
    innerCellList = list(innerCells.values())

    #build the outboard side surfaces
    outerSurfaces = {}
    offset = outerRadialBuildStart
    for key, value in outerBuildDict.items():
        outerSurfaces[key] = openmc.ZCylinder(r=offset)
        offset += value['thickness']

    outermostSurface = openmc.ZCylinder(r=offset, boundary_type = 'vacuum')

    #build the outboard side regions
    outerRegions = {}
    surfList = list(outerSurfaces.keys())
    for i in range(len(surfList)):
        if i != len(surfList)-1:
            outerRegions[surfList[i]] = -top & +bottom & +outerSurfaces[surfList[i]] & -outerSurfaces[surfList[i+1]]
        else:
            outerRegions[surfList[i]] = -top & +bottom & +outerSurfaces[surfList[i]] & -outermostSurface

    #build the outboard side cells
    outerCells = {}
    for key, value in outerBuildDict.items():
        if value['material'] == 'vacuum':
            outerCells[key] = openmc.Cell(region=outerRegions[key], name = key + ' outer',cell_id=outerBuildDict[key]['cell_id'])
        else:
            outerCells[key] = openmc.Cell(region=outerRegions[key], name = key + ' outer', fill = outerBuildDict[key]['material'],cell_id=outerBuildDict[key]['cell_id'])

    outerCellList = list(outerCells.values())

    #make the plasma cell
    plasmaRegion = -outerSurfaces['sol'] & +innerSurfaces['sol'] & +bottom & -top
    plasmaCell = openmc.Cell(region=plasmaRegion, name = 'plasma cell', cell_id=10001)
    
    cells = outerCellList + innerCellList
    cells.append(plasmaCell)

    geometry = openmc.Geometry(cells)

    return geometry
    
def main():
	materials = openmc.Materials.from_xml('materials.xml')
	vacVesselMat = materials[1]
	coilMat = materials[2]
	fwMat = materials[3]
	hts = materials[0]

	mat_dict = {
		    'fw':fwMat,
		    'vac_vessel':vacVesselMat,
		    'coils':coilMat
		    }



	##################### define geometry ########################

	fwInnerRadius = 750
	fwOuterRadius = 850
	height = 20
	plasmaRadius = 800

	innerBuildDict = {
		            "sol":{'thickness':5,'material':'vacuum','cell_id':1},
		            "fw":{'thickness':4,'material': fwMat,'cell_id':2},
		            "hts":{'thickness':5, 'material':hts,'cell_id':3},
		            "gap1":{'thickness':4,'material':'vacuum','cell_id':4},
		            "vv":{'thickness':5,'material':vacVesselMat,'cell_id':5},
		            "gap2":{'thickness':46,'material':'vacuum','cell_id':6},
		            "coils":{'thickness':52,'material':coilMat,'cell_id':7}
		            }

	outerBuildDict = {
		            "sol":{'thickness':5,'material':'vacuum','cell_id':8},
		            "fw":{'thickness':4,'material': fwMat,'cell_id':9},
		            "hts":{'thickness':5, 'material':hts,'cell_id':10},
		            "gap1":{'thickness':4,'material':'vacuum','cell_id':11},
		            "vv":{'thickness':5,'material':vacVesselMat,'cell_id':12},
		            "gap2":{'thickness':46,'material':'vacuum','cell_id':13},
		            "coils":{'thickness':52,'material':coilMat,'cell_id':14}
		            }

	geometry = buildGeometryFromDict(innerBuildDict, outerBuildDict, 750,850,20)

	geometry.export_to_xml()

	############## make some settings ################
	settings = openmc.Settings()

	#set up the source
	source = openmc.IndependentSource()
	radius = openmc.stats.Discrete([plasmaRadius],[1])
	z_range = openmc.stats.Uniform(a=-height/2,b=height/2)
	angle = openmc.stats.Uniform(a=0, b=2*np.pi)
	source.space = openmc.stats.CylindricalIndependent(r=radius, phi=angle,z=z_range,origin=(0.0,0.0,0.0))
	source.angle = openmc.stats.Isotropic()
	settings.source = [source]

	#run settings
	settings.run_mode = 'fixed source'
	settings.particles = 1000
	settings.batches = 10
	settings.photon_transport = True

	settings.export_to_xml()

	###########make some meshes (outer) (all these meshes are in the first cm of each layer)##############
	fwMeshOuter = openmc.CylindricalMesh(
		                        r_grid=np.array([fwOuterRadius,fwOuterRadius+1]),
		                        z_grid=np.array([-height/2,height/2]),
		                        phi_grid=  np.array([0,2*np.pi]),
		                        name = "fw outer",
		                        mesh_id=1
		                            )

	vvMeshOuter = openmc.CylindricalMesh(
		                            r_grid=np.array([fwOuterRadius+outerBuildDict['fw']
		                                             +outerBuildDict['gap1'],

		                                             fwOuterRadius+outerBuildDict['fw']
		                                             +outerBuildDict['gap1']+1]),
		                            z_grid=np.array([-height/2,height/2]),
		                            phi_grid=  np.array([0,2*np.pi]),
		                            name = 'vv mesh outer',
		                            mesh_id=2
		                            )

	coilMeshOuter = openmc.CylindricalMesh(
		                                r_grid=np.array([fwOuterRadius+outerBuildDict['fw']
		                                                 +outerBuildDict['gap1']
		                                                 +outerBuildDict['vac_vessel']
		                                                 +outerBuildDict['gap2'],

		                                                 fwOuterRadius+outerBuildDict['fw']
		                                                 +outerBuildDict['gap1']
		                                                 +outerBuildDict['vac_vessel']
		                                                 +outerBuildDict['gap2']+1]),
		                                z_grid=np.array([-height/2,height/2]),
		                                phi_grid=  np.array([0,2*np.pi]),
		                                name = 'coil mesh outer',
		                                mesh_id = 3
		                                )

	#make some meshes (inner)
	fwMeshInner = openmc.CylindricalMesh(
		                        r_grid=np.array([fwInnerRadius-1, fwInnerRadius]),
		                        z_grid=np.array([-height/2,height/2]),
		                        phi_grid=  np.array([0,2*np.pi]),
		                        name = 'fw mesh inner',
		                        mesh_id=4
		                            )

	vvMeshInner = openmc.CylindricalMesh(
		                            r_grid=np.array([fwInnerRadius
		                                             -innerBuildDict['fw']
		                                             -innerBuildDict['gap1']-1,

		                                             fwInnerRadius-innerBuildDict['fw']
		                                             -innerBuildDict['gap1']]),
		                            z_grid=np.array([-height/2,height/2]),
		                            phi_grid= np.array([0,2*np.pi]),
		                            name = 'vv mesh inner',
		                            mesh_id=5
		                            )

	coilMeshInner = openmc.CylindricalMesh(
		                                r_grid=np.array([fwInnerRadius-innerBuildDict['fw']
		                                                 -innerBuildDict['gap1']
		                                                 -innerBuildDict['vac_vessel']
		                                                 -innerBuildDict['gap2']-1,

		                                                fwInnerRadius-innerBuildDict['fw']
		                                                 -innerBuildDict['gap1']
		                                                 -innerBuildDict['vac_vessel']
		                                                 -innerBuildDict['gap2']]),
		                                z_grid=np.array([-height/2,height/2]),
		                                phi_grid= np.array([0,2*np.pi]),
		                                name = 'coil mesh inner',
		                                mesh_id=6
		                                )

	#make some tallies

	########################### FW tallies ######################
	fwOuterMeshFilter = openmc.MeshFilter(fwMeshOuter)
	fwInnerMeshFilter = openmc.MeshFilter(fwMeshInner)

	#Outer FW DPA
	fwOuterDPAtally = openmc.Tally(name="fw outer dpa tally")
	fwOuterDPAtally.filters = [fwOuterMeshFilter]
	fwOuterDPAtally.nuclides = ["Fe54", "Fe56", "Fe57", "Fe58"]
	fwOuterDPAtally.scores = ['damage-energy'] #eV/source

	#inner FW DPA
	fwInnerDPAtally = openmc.Tally(name="fw inner dpa tally")
	fwInnerDPAtally.filters = [fwInnerMeshFilter]
	fwInnerDPAtally.nuclides = ["Fe54", "Fe56", "Fe57", "Fe58"]
	fwInnerDPAtally.scores = ['damage-energy'] #eV/source

	################### VV tallies ############################
	vvOuterMeshFilter = openmc.MeshFilter(vvMeshOuter)
	vvInnerMeshFilter = openmc.MeshFilter(vvMeshInner)

	#Outer vv DPA
	vvOuterDPAtally = openmc.Tally(name="vv outer dpa tally")
	vvOuterDPAtally.filters = [vvOuterMeshFilter]
	vvOuterDPAtally.nuclides = ["Fe54", "Fe56", "Fe57", "Fe58"]
	vvOuterDPAtally.scores = ['damage-energy'] #eV/source

	#inner vv DPA
	vvInnerDPAtally = openmc.Tally(name="vv inner dpa tally")
	vvInnerDPAtally.filters = [vvInnerMeshFilter]
	vvInnerDPAtally.nuclides = ["Fe54", "Fe56", "Fe57", "Fe58"]
	vvInnerDPAtally.scores = ['damage-energy'] #eV/source

	#Outer vv He production
	vvOuterHetally = openmc.Tally(name='vv outer He tally')
	vvOuterHetally.filters = [vvOuterMeshFilter]
	vvOuterHetally.scores = ['He3-production', 'He4-production'] #particles/source

	#Inner vv He production
	vvInnerHetally = openmc.Tally(name='vv inner He tally')
	vvInnerHetally.filters = [vvInnerMeshFilter]
	vvInnerHetally.scores = ['He3-production', 'He4-production'] #particles/source

	###################### Coil Tallies #########################
	coilOuterMeshFilter = openmc.MeshFilter(coilMeshOuter)
	coilInnerMeshFilter = openmc.MeshFilter(coilMeshInner)
	coilOuterCellFilter = openmc.CellFilter([14])
	coilInnerCellFilter = openmc.CellFilter([7])
	fastNeutronFilter = openmc.EnergyFilter([0,0.1e6,18e6]) #just picked 18 for fun, anything over 14.1e6 should do
	neutronFilter = openmc.ParticleFilter(['neutron'])
	neutronPhotonFilter = openmc.ParticleFilter(['neutron', 'photon'])

	#Fast Flux (outer coils)
	coilOuterFluxTally = openmc.Tally(name = 'coil outer flux tally')
	coilOuterFluxTally.filters = [coilOuterMeshFilter, fastNeutronFilter, neutronFilter]
	coilOuterFluxTally.scores = ['flux'] #particle-cm/source

	#Fast Flux (Inner coils)
	coilInnerFluxTally = openmc.Tally(name = 'coil inner flux tally')
	coilInnerFluxTally.filters = [coilInnerMeshFilter, fastNeutronFilter, neutronFilter]
	coilInnerFluxTally.scores = ['flux'] #particle-cm/source

	#heating peak outer
	coilOuterHeatingMeshTally = openmc.Tally(name = 'coil outer heating mesh tally')
	coilOuterHeatingMeshTally.filters = [coilOuterMeshFilter, neutronPhotonFilter]
	coilOuterHeatingMeshTally.scores = ['heating'] #eV/source

	#heating peak Inner
	coilInnerHeatingMeshTally = openmc.Tally(name = 'coil inner heating mesh tally')
	coilInnerHeatingMeshTally.filters = [coilInnerMeshFilter, neutronPhotonFilter]
	coilInnerHeatingMeshTally.scores = ['heating'] #eV/source

	#heating total Outer
	coilOuterHeatingCellTally = openmc.Tally(name ='coil outer heating cell tally')
	coilOuterHeatingCellTally.filters = [coilOuterCellFilter, neutronPhotonFilter]
	coilOuterHeatingCellTally.scores = ['heating'] #eV/source

	#heating total Inner
	coilInnerHeatingCellTally = openmc.Tally(name ='coil inner heating cell tally')
	coilInnerHeatingCellTally.filters = [coilInnerCellFilter, neutronPhotonFilter]
	coilInnerHeatingCellTally.scores = ['heating'] #eV/source

	tallies = openmc.Tallies([
		                    fwOuterDPAtally,
		                    fwInnerDPAtally,
		                    vvOuterDPAtally,
		                    vvInnerDPAtally,
		                    vvOuterHetally,
		                    vvInnerHetally,
		                    coilOuterFluxTally,
		                    coilInnerFluxTally,
		                    coilOuterHeatingMeshTally,
		                    coilInnerHeatingMeshTally,
		                    coilOuterHeatingCellTally,
		                    coilInnerHeatingCellTally
		                    ])

	tallies.export_to_xml()

	#plot for checking
	p = openmc.Plot()
	p.width = (150, 150.0)
	p.pixels = (400, 400)
	p.color_by = 'material'

	plots = openmc.Plots([p])
	plots.export_to_xml()

	model = openmc.Model(geometry=geometry, materials=materials, settings=settings, tallies=tallies)

	model.export_to_model_xml('modelNeutronics.xml')
	
if __name__ == '__main__':main()