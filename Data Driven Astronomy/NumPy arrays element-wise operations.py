# Write your mean_datasets function here
import pathlib as pl
import numpy as np


def mean_datasets(mylist):
    arraycount = len(mylist)
    
    for i in range (1 , len(mylist)):
        sum_array = np.loadtxt(mylist[0], delimiter=",")
        myfile = pl.Path("d:/Dropbox/Public Documents/PythonScripts/Data Driven Astronomy/"+ myfilename)
        
        
        arr = np.loadtxt(myfile, delimiter=",")
        sum_array=sum_array+arr
        print(arr)
        print(sum_array)
    return arr


print(mean_datasets(["data1.csv", "data2.csv", "data3.csv"]))
