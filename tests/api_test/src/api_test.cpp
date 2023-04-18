#include <rogue/interfaces/api/Root.h>

int main (int argc, char **argv) {

   rogue::interfaces::api::Root root("pyrogue.examples","ExampleRoot");

   root.start();
   printf("Root started\n");

   // Using non pointer references
   printf("LocalTime = %s\n",root["LocalTime"].getDisp().c_str());
   root["AxiVersion"]["ScratchPad"].setDisp("0x1111");
   printf("ScratchPad = %s\n",root["AxiVersion"]["ScratchPad"].getDisp().c_str());

   // Get object as a pointer
   printf("ScratchPad = %s\n",root.getNode("ExampleRoot.AxiVersion.ScratchPad")->getDisp().c_str());

   // Get yaml config
   std::string cfg = root["GetYamlConfig"].call("True");
   printf("Config = %s\n", cfg.c_str());
   sleep(3);

   root.stop();
}

