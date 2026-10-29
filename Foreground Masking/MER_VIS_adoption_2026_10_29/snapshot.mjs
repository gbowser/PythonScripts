import fs from 'node:fs';
const saved=JSON.parse(fs.readFileSync('MER_VIS_adoption_2026_10_29/source_reviews.json'));
const boot=await(await fetch('http://127.0.0.1:8768/api/bootstrap')).json(),galaxies={};
for(const [id,r] of Object.entries(saved)){galaxies[id]=await(await fetch('http://127.0.0.1:8768/api/galaxy?id='+id+'&refit='+r.settings.refit_id)).json();if(galaxies[id].error)throw Error(galaxies[id].error)}
fs.writeFileSync('MER_VIS_adoption_2026_10_29/galaxies.json',JSON.stringify({boot,galaxies}));console.log('Read-only snapshot: '+Object.keys(galaxies).length+' displayed fits');
