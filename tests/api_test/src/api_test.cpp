#include <rogue/interfaces/api/Bsp.h>

void varListener(std::string path, std::string value) {
   printf("Var Listener: %s = %s\n", path.c_str(), value.c_str());
}

void varDone() {
   printf("Var Done\n");
}

int main (int argc, char **argv) {

   rogue::interfaces::api::Bsp bsp("pyrogue.examples","ExampleRoot");

   bsp.addVarListener(&varListener,&varDone);

   // Get running uptime clock
   printf("LocalTime = %s\n",bsp["LocalTime"].get().c_str());

   // Set and get scratchpad
   bsp["AxiVersion"]["ScratchPad"].setWrite("0x1111");
   printf("ScratchPad = %s\n",bsp["AxiVersion"]["ScratchPad"].readGet().c_str());

   // Get object as a pointer using full path, and get scratchpad
   printf("ScratchPad = %s\n",bsp.getNode("ExampleRoot.AxiVersion.ScratchPad")->get().c_str());

   // Get yaml config
   std::string cfg = bsp["GetYamlConfig"]("True");
   printf("Config = %s\n", cfg.c_str());

   // Set yaml config, example
   //bsp["SetYamlConfig"]("Some Yaml String");

   // Write Entrire Tree
   bsp["WriteAll"]();

   // Read Entrire Tree
   bsp["ReadAll"]();

   Py_BEGIN_ALLOW_THREADS;
   sleep(60);
   Py_END_ALLOW_THREADS;
}

