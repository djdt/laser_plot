Importing Data
==============

.. table:: Vendor formats supported by |pewpew|.

    +-------------+-------------+--------------+----------------+
    | Vendor      | Software    | Format       | Tested With    |
    +=============+=============+==============+================+
    | Agilent     | Mass Hunter | .b directory | 7500,7700,8900 |
    +-------------+-------------+--------------+----------------+
    | PerkinElmer |             | .xl files    |                |
    +-------------+-------------+--------------+----------------+
    | Thermo      | Qtegra      | .csv         | iCAP RQ        |
    +-------------+-------------+--------------+----------------+

For the majority of users importing data consists of dragging-and-dropping of files into |pewpew|.

Import Wizard
-------------

* **File -> Import -> Import Wizard**

The `Import Wizard` allows users to provide specific options when importing data and consists of three pages.
For programs that export lines as a directory of separate files the '.csv' import option should be used.

1. Select the data format.
    The data format will affect whether the path is to a file or folder and the import options.

2. Select the path to the data and format specific import options.
    Path selection uses the file dialog `Open File` or `Open Directory` or drag-and-drop of files into the wizard.
    Default import options are automatically filled in on path selection.

3. Select laser parameters and isotopes for import.
    If available, laser parameters will be read from the data.
    Isotopes names are editable by pressing the `Edit Names` button.


Kriss-Kross Import Wizard
-------------------------

* **File -> Import -> Kriss-Kross Import Wizard**

Import of Kriss-Kross_ collected Super-Resolution-Reconstruction images is performed
using the `Kriss-Kross Import Wizard`. This will guide users through import of the data
in a simliar manner to the :ref:`Import Wizard`.

1. Select the data format.
    The data format will affect whether the path is to a file or folder and the import options.

2. Select the path to the data and format specific import options.
    Paths are selected as in the :ref:`Import Wizard`, with the first path being the top layer of the 3D array.
    Selected paths can be reordered by dragging and a minimum of two paths must be selected.

3. Select laser parameters and isotopes for import.
    The wizard can only be completed once a valid configuration is input.

 .. _Kriss-Kross: https://doi.org/10.1021/acs.analchem.9b02380
