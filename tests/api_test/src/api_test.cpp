#include <rogue/interfaces/api/Root.h>
#include <rogue/interfaces/api/Variable.h>

int main (int argc, char **argv) {

   rogue::interfaces::api::RootPtr root = rogue::interfaces::api::Root::create("pyrogue.examples","ExampleRoot");

   root->start();
   printf("Root started\n");

   printf("LocalTime = %s\n",root->variable("LocalTime")->getDisp().c_str());
   root->device("AxiVersion")->variable("ScratchPad")->setDisp("0x1111");
   printf("ScratchPad = %s\n",root->device("AxiVersion")->variable("ScratchPad")->getDisp().c_str());

   sleep(5);

   root->stop();
}

