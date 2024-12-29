#from plot_gmm_feat import main as plot1GMM
from plot_gmm_feat import plotGMM

if __name__ == "__main__": # Esto es lo que se ejecuta si se llama al script directamente
    #plot1GMM
    my_list = [0.9, 0.5]
    my_list = [float(i) for i in my_list]
    plotGMM("./work/gmm/mfcc/SES007.gmm", 0, 1, my_list, "red", filesFeat=None, colorFeat=None, limits=None, subplot=111)
    
    