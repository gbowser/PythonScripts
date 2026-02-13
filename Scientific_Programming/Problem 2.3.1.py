base_seq='AGCTAGCAGTACGATCGTTTGGCAGTGG'
print('Fraction of A in base_seq: {:.2f}'.format(base_seq.count('A')/len(base_seq)))
print(f"Fraction of A in base_seq: {base_seq.count('A')/len(base_seq):.2f}")
print(f"Fraction of A in base_seq: {base_seq.count('A')/len(base_seq):.2%}")

print(f"Fraction of G & C in base_seq: {(base_seq.count('G')+base_seq.count('C'))/len(base_seq):.2%}")


seq = 'ACCTAGGT'
seqc = seq.replace('A', 't').replace('C', 'g').replace('G', 'c').replace('T', 'a').upper()
print(seqc)