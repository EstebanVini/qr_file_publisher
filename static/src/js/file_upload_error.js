/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { FileInput } from "@web/core/file_input/file_input";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

/**
 * The upload route used by the many2many_binary widget can be intercepted
 * by a reverse proxy (e.g. nginx rejecting the request with a 413 because
 * the file exceeds `client_max_body_size`) before it ever reaches Odoo. In
 * that case the response is an HTML error page instead of JSON, and
 * `uploadFiles` throws an uncaught `SyntaxError` from `JSON.parse`. This
 * patch turns that into a readable dialog for the end user.
 */
patch(FileInput.prototype, {
    setup() {
        super.setup();
        this.fileUploadErrorDialog = useService("dialog");
    },

    async uploadFiles(files) {
        try {
            return await super.uploadFiles(files);
        } catch (error) {
            const isServerUnreachable = error instanceof SyntaxError;
            this.fileUploadErrorDialog.add(AlertDialog, {
                title: _t("No se pudo subir el archivo"),
                body: isServerUnreachable
                    ? _t(
                        "El servidor rechazó el archivo antes de poder procesarlo. " +
                        "Esto suele pasar cuando el archivo supera el tamaño máximo " +
                        "permitido por el servidor. Probá con un archivo más chico o " +
                        "contactá al administrador del sistema."
                    )
                    : _t("Ocurrió un error inesperado al subir el archivo."),
            });
            return undefined;
        }
    },
});
