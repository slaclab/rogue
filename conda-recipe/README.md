
#### Building conda package

````
$ conda build -q conda-recipe --python --output-folder bld-dir -c defaults -c aires-tag -c lcls-ii -c conda-forge
$ conda activate
$ anaconda upload bld-dir/linux-64/rogue-.....
````
