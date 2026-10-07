import json
C=[]
def cell(p,r,ch,fp): C.append({'name':'pattern_set_cell','arguments':{'pattern':p,'row':r,'channel':ch,'effect':8,'effect_param':fp}})
# Apply only on existing attack cells and preserve their notes/volumes (tool merges omitted fields).
# Arp alternates quarter-phrase position.
arp_sections={1,2,3,4,5,6,7,8,9,11,12,13,14}
for p in arp_sections:
    for r in range(32): cell(p,r,1,205 if (r//4)%2==0 else 170)
# Main leads shift between left and center-left at phrase notes.
melrows={
2:[0,2,4,7,8,10,12,14,16,18,20,23,24,26,28,31],3:[0,2,4,6,8,10,12,14,16,18,20,22,24,27,28,30],4:[0,3,4,6,8,11,12,14,16,18,20,22,24,26,28,30],5:[0,2,4,7,8,10,12,15,16,18,20,22,24,27,28,30],6:[0,2,4,7,8,10,12,14,16,18,20,23,24,26,28,30],7:[0,2,4,6,8,11,12,14,16,18,20,22,24,26,28,30],8:[0,1,2,3,4,6,7,8,10,11,12,13,14,15,16,18,19,20,21,22,23,24,25,26,27,28,29,30,31],9:[0,1,2,3,4,6,7,8,9,10,11,12,13,14,15,16,18,19,20,21,22,23,24,25,26,27,28,29,30,31],12:[0,2,4,6,8,10,12,15,16,18,20,22,24,26,28,30],13:[0,2,4,7,8,10,12,14,16,18,20,22,24,26,28,30],14:[0,2,4,7,8,10,12,14,16,18,20,23,24,26,28,30]}
for p,rows in melrows.items():
    for r in rows: cell(p,r,0,48 if (r//8)%2==0 else 82)
for r in [0,4,8,12,16,20,24,28]: cell(1,r,0,66)
# Pluck and bell answer lines right.
pluck_sections={2,3,4,5,6,7,8,9,11,12,13,14}
for p in pluck_sections:
    for r in range(1,32,2): cell(p,r,5,58)
for p,rows in {0:[0,4,8,12,16,20,24,28],6:[1,5,9,13,17,21,25,29],7:[1,5,9,13,17,21,25,29],10:[0,6,12,16,22,28],11:[2,6,10,14,18,22,26,30]}.items():
    for r in rows: cell(p,r,6,216)
# Pad voice placement (existing chord attacks)
for p in [0,1,4,5,6,7,8,9,10,11,12,13,14]:
    for r in range(0,32,4):
        for ch,pan in [(8,54),(9,128),(10,202)]:cell(p,r,ch,pan)
open('/workspace/pan.json','w').write(json.dumps(C))
print(len(C))
