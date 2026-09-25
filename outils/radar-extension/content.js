// LABUSE Radar — inspecteur de page (référence).
//
// NOTE : ce fichier N'EST PAS injecté comme content-script persistant.
// Le service worker (background.js) injecte des fonctions équivalentes via
// chrome.scripting.executeScript (pas de content-script → moins d'empreinte,
// pas de permission "activeTab" nécessaire). On conserve ce fichier comme
// documentation lisible de ce que l'injection lit sur la page vivante.
//
// Retour de inspectPage() :
//   {
//     hasNext: bool,              // un contrôle "page suivante" existe
//     nextData: object|null,      // JSON de #__NEXT_DATA__ (page riche)
//     hasAditemContainer: bool,   // cartes DOM (page dégradée)
//     looksBlocked: bool,         // datadome / captcha / vérification
//     outerHTML: string,          // document.documentElement.outerHTML
//     indexDates: string[]        // index_date de chaque annonce
//   }
//
// clickNext() : clique le "page suivante" du site (navigation Next.js
// cliente qui préserve searchData) et renvoie true si le contrôle existait.
//
// La logique réelle vit dans background.js (fonctions inspectPage / clickNext)
// pour pouvoir être passée à executeScript sans dépendance externe.
