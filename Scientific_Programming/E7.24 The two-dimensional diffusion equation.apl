⍝ Two-dimensional diffusion on a square plate.
⍝ Dyalog APL-style script based on the Python version.

plateWidth←10
plateHeight←10
gridSpacingX←0.1
gridSpacingY←0.1
thermalDiffusivity←4

coolTemperature←300
hotTemperature←700

numPointsX←⌊plateWidth÷gridSpacingX
numPointsY←⌊plateHeight÷gridSpacingY

gridSpacingXSquared←gridSpacingX*2
gridSpacingYSquared←gridSpacingY*2
timeStep←(gridSpacingXSquared×gridSpacingYSquared)÷(2×thermalDiffusivity×(gridSpacingXSquared+gridSpacingYSquared))

hotRadius←2
hotCentreX←5
hotCentreY←5
hotRadiusSquared←hotRadius*2

numTimeSteps←101
plotSteps←0 10 50 100

currentTemperature←(numPointsX,numPointsY)⍴coolTemperature
nextTemperature←currentTemperature

⍝ Build the initial hot circular region.
:For xIndex :In ⍳numPointsX
    :For yIndex :In ⍳numPointsY
        xPosition←(xIndex-1)×gridSpacingX
        yPosition←(yIndex-1)×gridSpacingY
        distanceSquared←((xPosition-hotCentreX)*2)+((yPosition-hotCentreY)*2)
        :If distanceSquared<hotRadiusSquared
            currentTemperature[xIndex;yIndex]←hotTemperature
        :EndIf
    :EndFor
:EndFor

nextTemperature←currentTemperature

DoTimeStep←{
    current next←⍵
    next←current

    :For xIndex :In 2+⍳numPointsX-2
        :For yIndex :In 2+⍳numPointsY-2
            next[xIndex;yIndex]←current[xIndex;yIndex]+thermalDiffusivity×timeStep×(
                ((current[xIndex+1;yIndex])-(2×current[xIndex;yIndex])+(current[xIndex-1;yIndex]))÷gridSpacingXSquared
                +
                ((current[xIndex;yIndex+1])-(2×current[xIndex;yIndex])+(current[xIndex;yIndex-1]))÷gridSpacingYSquared
            )
        :EndFor
    :EndFor

    current←next
    current next
}

⎕←'Step   Time (ms)   Centre temperature (K)'
centreXIndex←1+⌊numPointsX÷2
centreYIndex←1+⌊numPointsY÷2

:For stepNumber :In ⍳numTimeSteps
    currentTemperature nextTemperature←DoTimeStep currentTemperature nextTemperature
    actualStep←stepNumber-1
    :If actualStep∊plotSteps
        ⎕←actualStep,(actualStep×timeStep×1000),currentTemperature[centreXIndex;centreYIndex]
    :EndIf
:EndFor
