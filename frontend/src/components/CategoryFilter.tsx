import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ChevronDownIcon, ChevronRight } from "lucide-react";
import React from "react";
import { CardContent } from "./ui/card";
import { Label } from "./ui/label";

const category_options: Record<string, string[]> = {
  "": ["pyiron_core"],
  pyiron_core: ["pyiron_workflow", "pyiron_nodes"],
  "pyiron_core>pyiron_nodes": [
    "atomistic",
    "databases",
    "controls",
    "math",
    "dev_tools",
    "plotting",
    "utilities",
    "dataframe",
    "executors",
  ],
  "pyiron_core>pyiron_nodes>dev_tools": [
    "parse_input_kwargs",
    "set_replacer",
    "register_libraries",
    "node_to_data_container",
    "extract_value",
    "filter_internals",
    "nested_dict_from_keys",
    "wf_data_class",
    "to_data_container",
  ],
  "pyiron_core>pyiron_nodes>atomistic": [
    "calculator",
    "assyst",
    "engine",
    "structure",
    "ml_potentials",
    "property",
  ],
  "pyiron_core>pyiron_nodes>atomistic>assyst": ["structures"],
  "pyiron_core>pyiron_nodes>atomistic>assyst>structures": [
    "ElementInput",
    "SpaceGroupInput",
    "SpaceGroupSampling",
  ],
  "pyiron_core>pyiron_nodes>atomistic>engine": ["lammps", "ase"],
  "pyiron_core>pyiron_nodes>atomistic>engine>ase": ["M3GNet", "GRACE", "EMT"],
  "pyiron_core>pyiron_nodes>atomistic>engine>lammps": [
    "CalcStatic",
    "Code1",
    "CalcMD",
    "compute_water_bonds_and_angles",
    "get_calculators",
    "Calc",
    "ParseLogFile",
    "ListPotentials",
    "InitLammps",
    "write_lammps_data_full",
    "extract_charges_from_lammps_potential",
    "Code",
    "CalcMinimize",
    "Tip3pData",
    "scale_number_in_string",
    "make_angles_array",
    "Shell",
    "GetEnergyPot",
    "InputCalcMinimizeLammps",
    "make_bonds_array",
    "ParseDumpFile",
    "DummyNode",
    "compute_water_bonds_indices",
    "Potential",
    "Lammps",
    "Collect",
    "ParseOutput",
  ],
  "pyiron_core>pyiron_workflow": ["simple_workflow"],
  "pyiron_core>pyiron_workflow>simple_workflow": [
    "_return_as_out_dataclass_node",
  ],
  "pyiron_core>pyiron_workflow>simple_workflow>_return_as_out_dataclass_node": [
    "<locals>",
  ],
  "pyiron_core>pyiron_workflow>simple_workflow>_return_as_out_dataclass_node><locals>":
    ["func_dataclass"],
  "pyiron_core>pyiron_nodes>atomistic>calculator": [
    "output",
    "generic",
    "data",
    "ase",
  ],
  "pyiron_core>pyiron_nodes>atomistic>calculator>data": [
    "InputCalcStatic",
    "InputCalcMinimize",
    "wfMetaData",
    "InputServer",
    "InputCalcMD",
  ],
  "pyiron_core>pyiron_nodes>atomistic>calculator>ase": [
    "Static",
    "StaticEnergy",
    "Minimize",
  ],
  "pyiron_core>pyiron_nodes>atomistic>calculator>generic": [
    "CreateSEFSContainer",
    "Static",
    "ApplyEngine",
  ],
  "pyiron_core>pyiron_nodes>atomistic>calculator>output": ["GetEnergyLast"],
  "pyiron_core>pyiron_nodes>atomistic>property": [
    "calphy",
    "phonons",
    "elastic",
  ],
  "pyiron_core>pyiron_nodes>atomistic>property>calphy": [
    "SolidFreeEnergy",
    "Tolerance",
    "Berendsen",
    "InputClass",
    "CalculatePhaseTransformationTemperature",
    "LiquidFreeEnergyWithTemperature",
    "SolidFreeEnergyWithTemperature",
    "LiquidFreeEnergy",
    "MD",
    "NoseHoover",
    "CollectResults",
    "ComputeTransitionTemperature",
  ],
  "pyiron_core>pyiron_nodes>atomistic>property>elastic": [
    "InputElasticTensor",
    "ComputeElasticConstants",
    "subjob_name",
    "GenerateStructures",
    "SymmetryAnalysis",
    "calculate_modulus",
    "ExtractFinalEnergy",
    "AddEnergies",
    "fit_elastic_matrix",
    "AnalyseStructures",
  ],
  "pyiron_core>pyiron_nodes>atomistic>property>phonons": [
    "GetDynamicalMatrix",
    "GetTotalDos",
    "GetThermalProperties",
    "ExtractFinalForces",
    "GetFreeEnergy",
    "GetAnalyticalFreeEnergy",
    "PhonopyParameters",
    "HasImaginaryModes",
    "phonopy",
    "PhonopyObject",
    "GetEigenvalues",
    "GenerateSupercells",
  ],
  "pyiron_core>pyiron_nodes>atomistic>structure": [
    "calc",
    "transform",
    "view",
    "build",
  ],
  "pyiron_core>pyiron_nodes>atomistic>structure>build": [
    "Bulk",
    "HighIndexSurface",
    "CubicBulkCell",
    "Surface",
  ],
  "pyiron_core>pyiron_nodes>atomistic>structure>calc": [
    "GetChemicalSpecies",
    "FitDiffPotential",
    "Volume",
    "LinearInterpolationDescriptor",
    "SplineDescriptor",
    "GetNeighbors",
    "SelectedIndex",
    "NumberOfAtoms",
    "GetDistances",
    "FitDiffPotential2",
  ],
  "pyiron_core>pyiron_nodes>atomistic>structure>transform": [
    "RotateAxisAngle",
    "Repeat",
    "FixSpecies",
    "CreateVacancy",
    "ApplyStrain",
  ],
  "pyiron_core>pyiron_nodes>atomistic>structure>view": ["Animate", "Plot3d"],
  "pyiron_core>pyiron_nodes>atomistic>ml_potentials": ["fitting"],
  "pyiron_core>pyiron_nodes>atomistic>ml_potentials>fitting": ["linearfit"],
  "pyiron_core>pyiron_nodes>atomistic>ml_potentials>fitting>linearfit": [
    "SavePotential",
    "PlotEnergyHistogram",
    "ReadPickledDatasetAsDataframe",
    "DesignMatrix",
    "make_linearfit",
    "GetVector",
    "SliceArray",
    "ParameterizePotentialConfig",
    "SplitTrainingAndTesting",
    "PlotEnergyFittingCurve",
    "MinMaxIndices",
    "ListDataSets",
    "PlotForcesFittingCurve",
    "PlotForcesHistogram",
    "PredictEnergiesAndForces",
    "RunLinearFit",
  ],
  "pyiron_core>pyiron_nodes>controls": [
    "ExtractList",
    "Filter",
    "GetAttribute",
    "pick_element",
    "iterate",
    "GetMask",
    "Print",
    "Code",
    "loop_until",
    "Slice",
    "SetAttribute",
    "InputVector",
    "recursive",
    "IterToDataFrame",
  ],
  "pyiron_core>pyiron_nodes>databases": ["node_hash_db", "elasticity"],
  "pyiron_core>pyiron_nodes>databases>elasticity": ["DeJong"],
  "pyiron_core>pyiron_nodes>databases>node_hash_db": [
    "GetHash",
    "CreateDB",
    "DeleteDB",
    "GetGraph",
    "ShowTable",
  ],
  "pyiron_core>pyiron_nodes>dataframe": [
    "GetColumnFromDataFrame",
    "MergeDataFrames",
    "DisplayDataFrame",
    "ApplyFunctionToSeriesNew",
    "ReadDataFrame",
    "GetRowsFromDataFrame",
    "ApplyFunctionToSeries",
  ],
  "pyiron_core>pyiron_nodes>executors": [
    "IterNode",
    "FluxClusterExecutor",
    "SingleNodeExecutor",
    "ProcessPoolExecutor",
    "fcc_metals",
    "FluxJobExecutor",
    "ThreadPoolExecutor",
  ],
  "pyiron_core>pyiron_nodes>math": [
    "Sin",
    "npMultiply",
    "Tan",
    "Sum",
    "Divide",
    "Arccos",
    "Mean",
    "Linspace",
    "BSpline",
    "Arcsin",
    "Range",
    "WeightedHistogram",
    "Identity",
    "b_spline_basis",
    "Shape",
    "aAddBC",
    "Multiply",
    "Array",
    "LinearBin",
    "b_spline_basis_derivative",
    "Add",
    "Arctan",
    "PseudoInverse",
    "Transpose",
    "Cos",
    "Reshape",
    "Arctan2",
    "SVDComponents",
    "Arange",
    "DotProduct",
    "SVD",
    "Subtract",
  ],
  "pyiron_core>pyiron_nodes>plotting": [
    "ShowArray",
    "AnalyseConvergencePlot",
    "MultiPlot",
    "Scatter",
    "Plot",
    "PlotDataFrameXY",
    "Subplot",
    "PlotDataFrame",
    "Title",
    "LinearFittingCurve",
    "Histogram",
  ],
  "pyiron_core>pyiron_nodes>utilities": [
    "Range",
    "Linspace",
    "Prepend",
    "List5",
    "Append",
    "Slice",
    "GetItem",
    "Index",
  ],
};

interface CategoryFilterProps {
  category: string;
  categoryOptions: Record<string, string[]>;
  onCategoryChange: (category: string) => void;
}

export const CategoryFilter: React.FC<CategoryFilterProps> = ({
  category,
  categoryOptions,
  onCategoryChange,
}) => {
  const optionsByPath =
    Object.keys(categoryOptions).length > 0
      ? categoryOptions
      : category_options;

  const appendPath = (path: string, option: string) => {
    if (path != "") return path + ">" + option;
    else return option;
  };
  const subPaths = category.split(">").map((elem, i, arr) => ({
    elem,
    path: arr.slice(0, i + 1).join(">"),
    prev: arr.slice(0, i).join(">"),
  }));
  const breadcrumbs =
    category !== "" &&
    subPaths.map((subPath) => (
      <React.Fragment key={subPath.path}>
        <BreadcrumbItem className="border rounded-md bg-popover p-2">
          <DropdownMenu>
            <DropdownMenuTrigger className="flex items-center gap-1">
              {subPath.elem}
              <ChevronDownIcon className="size-3.5" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              <DropdownMenuGroup>
                {(optionsByPath[subPath.prev] || []).map((option) => (
                  <DropdownMenuItem
                    key={option}
                    onClick={() =>
                      onCategoryChange(appendPath(subPath.prev, option))
                    }
                  >
                    {option}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuGroup>
            </DropdownMenuContent>
          </DropdownMenu>
        </BreadcrumbItem>
        <BreadcrumbSeparator>
          <ChevronRight />
        </BreadcrumbSeparator>
      </React.Fragment>
    ));
  return (
    <CardContent className="border-b  pb-4 space-y-2">
      <Label>Category Filter</Label>
      <Breadcrumb>
        <BreadcrumbList>
          {breadcrumbs}{" "}
          <BreadcrumbItem className="border rounded-md bg-popover p-2">
            <DropdownMenu>
              <DropdownMenuTrigger className="flex items-center gap-1">
                ...
                <ChevronDownIcon className="size-3.5" />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start">
                <DropdownMenuGroup>
                  {(optionsByPath[category] || []).map((option) => (
                    <DropdownMenuItem
                      key={option}
                      onClick={() =>
                        onCategoryChange(appendPath(category, option))
                      }
                    >
                      {option}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuGroup>
              </DropdownMenuContent>
            </DropdownMenu>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
    </CardContent>
  );
};
