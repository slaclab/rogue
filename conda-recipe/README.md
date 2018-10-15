
#### Building conda package

````
$ conda build -q conda-recipe --python=3.6 --output-folder bld-dir -c conda-forge -c paulscherrerinstitute
$ conda activate
$ anaconda upload bld-dir/linux-64/rogue-v2.12.1-0.tar.bz2
````
