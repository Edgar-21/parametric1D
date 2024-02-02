import openmc

def buildGeometryFromDict(innerBuildDict, outerBuildDict, innerRadialBuildStart, outerRadialBuildStart, height, NWL=False):
	#build dict {'layer_name' : {'thickness': float, 'material': openmc material}}
	#define surfaces
	top = openmc.ZPlane(z0=height/2, boundary_type='periodic', surface_id = 10001)
	bottom = openmc.ZPlane(z0=-height/2, boundary_type='periodic', surface_id=10002)
	if not NWL:
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

		return geometry, innerCells, outerCells
	else:
		#build the inboard side surfaces/regions
		innerSurfaces = {}
		offset = innerRadialBuildStart
		i = 0
		for key, value in innerBuildDict.items():
			if i < 1:
				innerSurfaces[key] = openmc.ZCylinder(r=offset)
				offset -= value['thickness']
				i+=1
			else:
				innerSurfaces[key] = openmc.ZCylinder(r=offset, boundary_type = 'vacuum', surface_id = 10003)
				break

		innerSurfacesList = list(innerSurfaces.values())

		innerSOLregion = -top & -bottom & -innerSurfacesList[0] & + innerSurfacesList[1]

		#build the outboard side surfaces/regions
		outerSurfaces = {}
		offset = outerRadialBuildStart
		i = 0
		for key, value in outerBuildDict.items():
			if i < 1:
				outerSurfaces[key] = openmc.ZCylinder(r=offset)
				offset += value['thickness']
				i+=1
			else:
				outerSurfaces[key] = openmc.ZCylinder(r=offset, boundary_type = 'vacuum', surface_id = 10004)
				break

		outerSurfacesList = list(outerSurfaces.values())

		outerSOLregion = -top & -bottom & +outerSurfacesList[0] & -outerSurfacesList[1]

		plasmaRegion = -top & -bottom & +innerSurfacesList[0] & -outerSurfacesList[1]

		#make the cells
		innerSOLCell = openmc.Cell(region=innerSOLregion)
		outerSOLCell = openmc.Cell(region=outerSOLregion)
		plasmaCell = openmc.Cell(region=plasmaRegion)

		cellDict = {'innerSOLcell': innerSOLCell, 'outerSOLcell': outerSOLCell, "plasmaCell":plasmaCell}

		geometry = openmc.Geometry([innerSOLCell, plasmaCell, outerSOLCell])

		return geometry, cellDict
			
	
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
					"fwCellTally":{'thickness':1,'material': fwMat,'cell_id':2},
					"fw":{'thickness':4,'material': fwMat,'cell_id':3},
					"hts":{'thickness':5, 'material':hts,'cell_id':4},
					"gap1":{'thickness':4,'material':'vacuum','cell_id':5},
					"vvCellTally":{'thickness':1,'material':vacVesselMat,'cell_id':6},
					"vv":{'thickness':9,'material':vacVesselMat,'cell_id':7},
					"gap2":{'thickness':46,'material':'vacuum','cell_id':8},
					"coilCellTally":{'thickness':1,'material':coilMat,'cell_id':9},
					"coils":{'thickness':51,'material':coilMat,'cell_id':10}
					}

	outerBuildDict = {
					"sol":{'thickness':5,'material':'vacuum','cell_id':11},
					"fwCellTally":{'thickness':1,'material': fwMat,'cell_id':12},
					"fw":{'thickness':4,'material': fwMat,'cell_id':13},
					"hts":{'thickness':5, 'material':hts,'cell_id':14},
					"gap1":{'thickness':4,'material':'vacuum','cell_id':15},
					"vvCellTally":{'thickness':1,'material':vacVesselMat,'cell_id':16},
					"vv":{'thickness':9,'material':vacVesselMat,'cell_id':17},
					"gap2":{'thickness':46,'material':'vacuum','cell_id':18},
					"coilCellTally":{'thickness':1,'material':coilMat,'cell_id':19},
					"coils":{'thickness':51,'material':coilMat,'cell_id':20}
					}

	geometry, innerCells, outerCells = buildGeometryFromDict(innerBuildDict, outerBuildDict, 750,850,20)

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

	#make some tallies

	########################### FW tallies ######################
	fwInnerCellFilter = openmc.CellFilter(innerCells['fwCellTally'])
	fwOuterCellFilter = openmc.CellFilter(outerCells['fwCellTally'])

	#Outer FW DPA
	fwOuterDPAtally = openmc.Tally(name="fw outer dpa tally")
	fwOuterDPAtally.filters = [fwOuterCellFilter]
	fwOuterDPAtally.nuclides = ["Fe54", "Fe56", "Fe57", "Fe58"]
	fwOuterDPAtally.scores = ['damage-energy'] #eV/source

	#inner FW DPA
	fwInnerDPAtally = openmc.Tally(name="fw inner dpa tally")
	fwInnerDPAtally.filters = [fwInnerCellFilter]
	fwInnerDPAtally.nuclides = ["Fe54", "Fe56", "Fe57", "Fe58"]
	fwInnerDPAtally.scores = ['damage-energy'] #eV/source

	################### VV tallies ############################
	vvOuterCellFilter = openmc.CellFilter(outerCells['vvCellTally'])
	vvInnerCellFilter = openmc.CellFilter(innerCells['vvCellTally'])

	#Outer vv DPA
	vvOuterDPAtally = openmc.Tally(name="vv outer dpa tally")
	vvOuterDPAtally.filters = [vvOuterCellFilter]
	vvOuterDPAtally.nuclides = ["Fe54", "Fe56", "Fe57", "Fe58"]
	vvOuterDPAtally.scores = ['damage-energy'] #eV/source

	#inner vv DPA
	vvInnerDPAtally = openmc.Tally(name="vv inner dpa tally")
	vvInnerDPAtally.filters = [vvInnerCellFilter]
	vvInnerDPAtally.nuclides = ["Fe54", "Fe56", "Fe57", "Fe58"]
	vvInnerDPAtally.scores = ['damage-energy'] #eV/source

	#Outer vv He production
	vvOuterHetally = openmc.Tally(name='vv outer He tally')
	vvOuterHetally.filters = [vvOuterCellFilter]
	vvOuterHetally.scores = ['He3-production', 'He4-production'] #particles/source

	#Inner vv He production
	vvInnerHetally = openmc.Tally(name='vv inner He tally')
	vvInnerHetally.filters = [vvInnerCellFilter]
	vvInnerHetally.scores = ['He3-production', 'He4-production'] #particles/source

	###################### Coil Tallies #########################
	coilOuterCellFilter = openmc.CellFilter(outerCells['coilCellTally'])
	coilInnerCellFilter = openmc.CellFilter(innerCells['coilCellTally'])
	coilOuterCellFilter = openmc.CellFilter([outerCells['coils'], outerCells['coilCellTally']])
	coilInnerCellFilter = openmc.CellFilter([innerCells['coils'], innerCells['coilCellTally']])
	fastNeutronFilter = openmc.EnergyFilter([0,0.1e6,18e6]) #just picked 18 for fun, anything over 14.1e6 should do
	neutronFilter = openmc.ParticleFilter(['neutron'])
	neutronPhotonFilter = openmc.ParticleFilter(['neutron', 'photon'])

	#Fast Flux (outer coils)
	coilOuterFluxTally = openmc.Tally(name = 'coil outer flux tally')
	coilOuterFluxTally.filters = [coilOuterCellFilter, fastNeutronFilter, neutronFilter]
	coilOuterFluxTally.scores = ['flux'] #particle-cm/source

	#Fast Flux (Inner coils)
	coilInnerFluxTally = openmc.Tally(name = 'coil inner flux tally')
	coilInnerFluxTally.filters = [coilInnerCellFilter, fastNeutronFilter, neutronFilter]
	coilInnerFluxTally.scores = ['flux'] #particle-cm/source

	#heating peak outer
	coilOuterHeatingPeakTally = openmc.Tally(name = 'coil outer heating mesh tally')
	coilOuterHeatingPeakTally.filters = [coilOuterCellFilter, neutronPhotonFilter]
	coilOuterHeatingPeakTally.scores = ['heating'] #eV/source

	#heating peak Inner
	coilInnerHeatingPeakTally = openmc.Tally(name = 'coil inner heating mesh tally')
	coilInnerHeatingPeakTally.filters = [coilInnerCellFilter, neutronPhotonFilter]
	coilInnerHeatingPeakTally.scores = ['heating'] #eV/source

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
							coilOuterHeatingPeakTally,
							coilInnerHeatingPeakTally,
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
