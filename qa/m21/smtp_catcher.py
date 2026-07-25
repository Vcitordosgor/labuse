"""Serveur SMTP local de CAPTURE (preuve d'envoi réel M21, sans secret Gmail).

Reçoit de VRAIS messages SMTP (socket réel, transaction complète) et les écrit dans un
fichier — c'est un « envoi réel » vers un serveur local, pas un mock. Utilisé pour prouver
le transport + les 4 mécaniques sans le mot de passe de production (que seul Vic détient).

Usage :  python qa/m21/smtp_catcher.py <port> <fichier_sortie>
"""
import asyncore
import smtpd
import sys


class Catcher(smtpd.SMTPServer):
    def __init__(self, localaddr, outfile):
        super().__init__(localaddr, None)
        self.outfile = outfile

    def process_message(self, peer, mailfrom, rcpttos, data, **kw):
        body = data.decode("utf-8", "replace") if isinstance(data, (bytes, bytearray)) else str(data)
        with open(self.outfile, "a", encoding="utf-8") as f:
            f.write("\n===== MESSAGE REÇU (SMTP) =====\n")
            f.write(f"[enveloppe] MAIL FROM={mailfrom}  RCPT TO={rcpttos}\n")
            f.write(body)
            f.write("\n===== FIN MESSAGE =====\n")
        print(f"[catcher] message reçu de {mailfrom} pour {rcpttos}", flush=True)
        return None


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 1025
    outfile = sys.argv[2] if len(sys.argv) > 2 else "/tmp/labuse_mail_capture.txt"
    open(outfile, "w").close()  # reset
    Catcher(("127.0.0.1", port), outfile)
    print(f"[catcher] écoute 127.0.0.1:{port} → {outfile}", flush=True)
    asyncore.loop()
