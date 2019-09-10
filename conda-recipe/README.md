
#### Building conda package

````
$ conda build -q conda-recipe --python --output-folder bld-dir -c defaults -c tidair-packages -c conda-forge
$ conda activate
$ anaconda upload bld-dir/linux-64/rogue-.....
````
