# Training Dummies
Training Dummies module for cmangos vanilla and tbc cores which will add training dummies to the capital cities

# Available Cores
Classic and TBC

# How to install
1. Follow the instructions in https://github.com/davidonete/cmangos-modules?tab=readme-ov-file#how-to-install
2. Enable the `BUILD_MODULE_TRAININGDUMMIES` flag in cmake and run cmake. The module should be installed in `src/modules/trainingdummies`
3. Copy the configuration file from `src/modules/trainingdummies/src/trainingdummies.conf.dist.in` and place it where your mangosd executable is. Also rename it to `trainingdummies.conf`.
4. Remember to edit the config file and modify the options you want to use.
5. Lastly you will have to install the database changes located in the `src/modules/trainingdummies/sql/install` folder, each folder inside represents where you should execute the queries. E.g. The queries inside of `src/modules/trainingdummies/sql/install/world` will need to be executed in the world/mangosd database, the ones in `src/modules/trainingdummies/sql/install/characters` in the characters database, etc...

# How to uninstall
To remove the training dummies from your server you have multiple options, the first and easiest is to disable it from the `trainingdummies.conf` file. The second option is to completely remove it from the server and db:
1. Remove the `BUILD_MODULE_TRAININGDUMMIES` flag from your cmake configuration and recompile the game
2. Execute the sql queries located in the `src/modules/trainingdummies/sql/uninstall` folder. Each folder inside represents where you should execute the queries. E.g. The queries inside of `src/modules/trainingdummies/sql/uninstall/world` will need to be executed in the world/mangosd database, the ones in `src/modules/trainingdummies/sql/uninstall/characters` in the characters database, etc...
