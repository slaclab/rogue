
#### Building conda package

````
$ conda build -q conda-recipe-ne --python --output-folder bld-dir-ne -c defaults -c conda-forge
$ conda activate
$ anaconda upload bld-dir/linux-64/rogue-.....
````
