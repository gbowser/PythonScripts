#A DNA sequence encodes each amino acide making up a protein  as  3-nculeotiede dquence called a codon.  For example, the codon  ATG  encodes the amino acid methionine.  The genetic code is redundant, meaning that most amino acids are encoded by more than one codon.  For example, the amino acid leucine is encoded by the codons TTA, TTG, CTT, CTC, CTA, and CTG.  Write a Python program that reads in a DNA sequence and counts the number of times each amino acid is encoded in the sequence.  
# The sequence may find it useful to store the genetic code in a dictionary.    
# AGT CTT ATA TCT contains codone ATG, CTT , ATA, TCT




# 1st frame = from first position to 3rd position
# 2nd frame = from second position to 4th position
# 3rd frame = from third position to 5th position

def codon_list(dna_sequence, frame):
    codons = []
    for i in range(frame, len(dna_sequence)-2, 3):
        codons.append(dna_sequence[i:i+3])  
    return codons

dna_sequence = "AGTCTTATATCT"
frame = 1
print(f"The codons in the frame are: {codon_list(dna_sequence, frame)}")

