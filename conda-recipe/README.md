
#### Building conda package

````
$ conda build --debug conda-recipe --output-folder bld-dir -c conda-forge -c pydm-tag
$ conda activate
$ miniforge upload bld-dir/linux-64/rogue-.....
````
