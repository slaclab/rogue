
#include <rogue/hardware/pgp/PgpCard.h>
#include <rogue/hardware/pgp/Info.h>
#include <stdio.h>

namespace rhp = rogue::hardware::pgp;

int main(int argc, char **argv) {

   rhp::PgpCardPtr pgp = rhp::PgpCard::create();

   pgp->open("/dev/pgpcard_0",0,0);

   rhp::InfoPtr info = pgp->getInfo();

   printf("Version: 0x%.8x, Build: %s\n",info->version,info->buildStamp);
}

