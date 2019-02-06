from matplotlib import pyplot as plt
from matplotlib import cm
import numpy as np
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
from collections import OrderedDict

class KRbCustomColors:
	def __init__(self):
		self.whitePlasma = self.makeWhitePlasma()
		self.whiteJet = self.makeWhiteJet()
		self.whiteMagma = self.makeWhiteMagma()

	def makeWhitePlasma(self):
		# Default colorbar
		plasma = cm.get_cmap('plasma', 256)

		N = 256
		vals = np.ones((N, 4))
		vals[:,0] *= plasma.colors[-1][0]
		vals[:,1] *= plasma.colors[-1][1]
		vals[:,2] *= plasma.colors[-1][2]
		a = np.linspace(0, 1, N)
		vals[:, 3] = a**2
		whitePlasmaStart = ListedColormap(vals)

		whitePlasmaColors = np.vstack((whitePlasmaStart(np.linspace(0, 1, 128)),
		                       plasma(np.linspace(1, 0, 384))))
		return ListedColormap(whitePlasmaColors, name='WhitePlasma')

	def makeWhiteMagma(self):
		# Default colorbar
		magma = cm.get_cmap('magma', 256)

		N = 256
		vals = np.ones((N, 4))
		vals[:,0] *= magma.colors[-1][0]
		vals[:,1] *= magma.colors[-1][1]
		vals[:,2] *= magma.colors[-1][2]
		a = np.linspace(0, 1, N)
		vals[:, 3] = a**2
		whiteMagmaStart = ListedColormap(vals)

		whiteMagmaColors = np.vstack((whiteMagmaStart(np.linspace(0, 1, 128)),
		                       magma(np.linspace(1, 0, 384))))
		return ListedColormap(whiteMagmaColors, name='WhiteMagma')

	def makeWhiteJet(self):
		colors = [
			(1,1,1), # White
			(51.0/256, 11.0/256, 130.0/256), # Purple
			(39.0/256, 205.0/256, 247.0/256), # Cyan
			(39.0/256, 247.0/256, 122.0/256), # Green
			(247.0/256, 240.0/256, 39.0/256), # Yellow
			(247.0/256, 174.0/256, 39.0/256), # Orange
			(255.0/256, 10.0/256, 10/256), # Red
		]  # R -> G -> B
		interp = 100

		# Create the colormap
		return LinearSegmentedColormap.from_list('WhiteJet', colors, N=interp)


def plot_examples(cms):
    """
    helper function to plot two colormaps
    """
    np.random.seed(19680801)
    poo = np.random.randn(30, 30)

    data = np.ones((30, 30)).astype(float)
    for i in range(30):
    	for j in range(30):
    		data[i,j] = np.exp(-((i-15)**2 + (j-15)**2) / 5.0**2)

    data = 15*data + poo

    fig, axs = plt.subplots(1, 2, figsize=(6, 3), constrained_layout=True)
    for [ax, cmap] in zip(axs, cms):
        psm = ax.pcolormesh(data, cmap=cmap, vmin=0, vmax=15)
        fig.colorbar(psm, ax=ax)
    plt.show()

if __name__ == "__main__":
	cm = KRbCustomColors()
	plot_examples([cm.whiteJet, cm.whitePlasma])