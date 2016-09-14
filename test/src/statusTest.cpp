
#include "PgpCard.h"
#include <stdio.h>

int main(int argc, char **argv) {

   PgpCard *pgp = new PgpCard();

   pgp->openWo("/dev/pgpcard_0");

   PgpInfo * info = pgp->getInfo();

   printf("Version: 0x%.8x, Build: %s\n",info->version,info->buildStamp);
}

