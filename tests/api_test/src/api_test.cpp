#include <rogue/interfaces/api/Root.h>

void varListener(std::string path, std::string value) {
   printf("Var Listener: %s = %s\n", path.c_str(), value.c_str());
}

void rootListener(std::string path, std::string value) {
   printf("Root Listener: %s = %s\n", path.c_str(), value.c_str());
}

void rootDone() {
   printf("Root Done\n");
}

int main (int argc, char **argv) {
   uint32_t x;

   rogue::interfaces::api::Root root("pyrogue.examples","ExampleRoot");

   root.start();
   printf("Root started\n");

   root.addVarListener(&rootListener,&rootDone);
   root["LocalTime"].addListener(&varListener);

   // Get running uptime clock
   printf("LocalTime = %s\n",root["LocalTime"].getDisp().c_str());

   // Set and get scratchpad
   root["AxiVersion"]["ScratchPad"].setDisp("0x1111");
   printf("ScratchPad = %s\n",root["AxiVersion"]["ScratchPad"].getDisp().c_str());

   // Get object as a pointer using full path, and get scratchpad
   printf("ScratchPad = %s\n",root.getNode("ExampleRoot.AxiVersion.ScratchPad")->getDisp().c_str());

   // Get yaml config
   std::string cfg = root["GetYamlConfig"].call("True");
   printf("Config = %s\n", cfg.c_str());

   // Set yaml config, example
   //root["SetYamlConfig"].call("Some Yaml String");

   Py_BEGIN_ALLOW_THREADS;
   sleep(60);
   Py_END_ALLOW_THREADS;

   root.stop();
}

