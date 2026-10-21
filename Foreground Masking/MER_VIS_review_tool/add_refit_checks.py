from pathlib import Path
p=Path('MER_VIS_review_tool/test_calculations.mjs');s=p.read_text(encoding='utf8');s+='''
const transform={rect:{left:100,top:50},left:20,top:10,w:400,h:200,view:[700,900,800,900]};
assert.deepEqual(Array.from(tool.imagePixel(transform,320,160)),[800,850]);
assert.deepEqual(Array.from(tool.imagePixel(transform,120,60)),[700,900]);
assert.deepEqual(Array.from(tool.imagePixel(transform,520,260)),[900,800]);
assert.equal(context.defaultSettings(g).display.stretch,'autostf');
console.log('PASS: screen-to-native-pixel centre mapping at zoomed view boundaries and centre.');
''';p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/test_review_MER_VIS.py');s=p.read_text(encoding='utf8');s=s.replace("    def test_native_pixels_and_byte_orientation(self):", '''    def test_refit_validation_and_origin(self):
        oid='-586374330510251740'
        for payload in [dict(object_id=oid,x=-1,y=2),dict(object_id=oid,x=float('nan'),y=2),dict(object_id=oid,x=True,y=2),dict(object_id='unknown',x=2,y=2)]:
            with self.assertRaises((ValueError,KeyError)):self.store.start_refit(payload)
        for job in ['../outside','g'*32]:
            with self.assertRaises(ValueError):self.store.refit_status(job)
        req=urllib.request.Request(self.url+'/api/refit',data=b'{}',headers={'Content-Type':'application/json','Origin':'https://not-local.example','X-Review-Token':'test-token'})
        with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(req)
        self.assertEqual(error.exception.code,403)

    def test_native_pixels_and_byte_orientation(self):''');p.write_text(s,encoding='utf8')
