import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
const [template,css,js]=await Promise.all(['merchant-preview.template.html','merchant-app.css','merchant-app.js'].map(file=>fs.readFile(path.join(root,file),'utf8')));
const html=template.replace('<!-- MERCHANT_STYLES -->',()=>'<style>\n'+css+'\n</style>').replace('<!-- MERCHANT_SCRIPT -->',()=>'<script>\n'+js+'\n</script>');
await fs.writeFile(path.join(root,'design-handoff.html'),html);
console.log('Built frontend/design-handoff.html');
