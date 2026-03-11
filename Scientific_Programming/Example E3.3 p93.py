import matplotlib.pyplot as plt
import numpy as np

# Matplotlib troubleshooting checklist:
# 1. Choose output mode first:
#    - Use plt.show() for an interactive window.
#    - Use plt.savefig(...) for a file-only script.
# 2. Remember that plt.show() blocks until the window is closed. That is
#    normal GUI behavior, not usually a hang.
# 3. With usetex=True, the first render can be slower because Matplotlib calls
#    external latex/dvipng tools.
# 4. If something appears stuck, switch temporarily from plt.show() to
#    plt.savefig(...) to tell GUI issues from LaTeX/rendering issues.
# 5. Avoid timed auto-close patterns with Tk unless you have tested them:
#    plt.show(block=False), plt.pause(...), and plt.close() can trigger
#    backend shutdown errors on some Python/Matplotlib combinations.
#
# Use the external LaTeX toolchain for text rendering.
plt.rc('text', usetex=True)

x = np.linspace(-10, 10, 1001)
line_styles = ['-', '--', ':', '-.']

for n in range(1, 5):
    y = x**n * np.sin(x)
    y /= max(y)

    plt.plot(x, y, linestyle=line_styles[n - 1], label=rf'$x^{{{n}}}\sin x$')

             

plt.legend(loc='lower center')
plt.savefig('Scientific_Programming/Example E3.3 p93.png', dpi=150, bbox_inches='tight')
print('Close the plot window to end the program.')
plt.show()

t=np.linspace(0, 2,1000)
f=t*np.exp(t+np.sin(20*t))
plt.plot(t,f)
plt.xlim(1.5,1.8)
plt.ylim(0,30)
plt.savefig('Scientific_Programming/Example p96.png', dpi=150, bbox_inches='tight')
print('Close the plot window to end the program.')
plt.show()
