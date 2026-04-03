OPTION BASE 1

CONST plateWidth = 10#
CONST plateHeight = 10#
CONST gridSpacingX = 0.1#
CONST gridSpacingY = 0.1#
CONST thermalDiffusivity = 4#

CONST coolTemperature = 300#
CONST hotTemperature = 700#

CONST numPointsX = 100
CONST numPointsY = 100

CONST gridSpacingXSquared = gridSpacingX * gridSpacingX
CONST gridSpacingYSquared = gridSpacingY * gridSpacingY
CONST timeStep = (gridSpacingXSquared * gridSpacingYSquared) / (2# * thermalDiffusivity * (gridSpacingXSquared + gridSpacingYSquared))

CONST hotRadius = 2#
CONST hotCentreX = 5#
CONST hotCentreY = 5#
CONST hotRadiusSquared = hotRadius * hotRadius

CONST numTimeSteps = 101

DIM currentTemperature(1 TO numPointsX, 1 TO numPointsY) AS DOUBLE
DIM nextTemperature(1 TO numPointsX, 1 TO numPointsY) AS DOUBLE

DECLARE SUB SetInitialTemperature (temperature() AS DOUBLE)
DECLARE SUB DoTimeStep (currentTemperature() AS DOUBLE, nextTemperature() AS DOUBLE)

CALL SetInitialTemperature(currentTemperature())

FOR xIndex = 1 TO numPointsX
    FOR yIndex = 1 TO numPointsY
        nextTemperature(xIndex, yIndex) = currentTemperature(xIndex, yIndex)
    NEXT yIndex
NEXT xIndex

PRINT "Step", "Time (ms)", "Centre temperature (K)"

FOR stepNumber = 0 TO numTimeSteps - 1
    CALL DoTimeStep(currentTemperature(), nextTemperature())

    FOR xIndex = 1 TO numPointsX
        FOR yIndex = 1 TO numPointsY
            currentTemperature(xIndex, yIndex) = nextTemperature(xIndex, yIndex)
        NEXT yIndex
    NEXT xIndex

    IF stepNumber = 0 OR stepNumber = 10 OR stepNumber = 50 OR stepNumber = 100 THEN
        PRINT stepNumber, stepNumber * timeStep * 1000#, currentTemperature(numPointsX \ 2, numPointsY \ 2)
    END IF
NEXT stepNumber

END

SUB SetInitialTemperature (temperature() AS DOUBLE)
    FOR xIndex = 1 TO numPointsX
        xPosition = (xIndex - 1) * gridSpacingX

        FOR yIndex = 1 TO numPointsY
            yPosition = (yIndex - 1) * gridSpacingY
            temperature(xIndex, yIndex) = coolTemperature

            distanceSquared = (xPosition - hotCentreX) ^ 2 + (yPosition - hotCentreY) ^ 2
            IF distanceSquared < hotRadiusSquared THEN
                temperature(xIndex, yIndex) = hotTemperature
            END IF
        NEXT yIndex
    NEXT xIndex
END SUB

SUB DoTimeStep (currentTemperature() AS DOUBLE, nextTemperature() AS DOUBLE)
    ' Start from the current temperature field so the edges stay unchanged.
    FOR xIndex = 1 TO numPointsX
        FOR yIndex = 1 TO numPointsY
            nextTemperature(xIndex, yIndex) = currentTemperature(xIndex, yIndex)
        NEXT yIndex
    NEXT xIndex

    ' Update only interior points using the four nearest neighbours.
    FOR xIndex = 2 TO numPointsX - 1
        FOR yIndex = 2 TO numPointsY - 1
            nextTemperature(xIndex, yIndex) = currentTemperature(xIndex, yIndex) + thermalDiffusivity * timeStep * ( _
                (currentTemperature(xIndex + 1, yIndex) - 2# * currentTemperature(xIndex, yIndex) + currentTemperature(xIndex - 1, yIndex)) / gridSpacingXSquared + _
                (currentTemperature(xIndex, yIndex + 1) - 2# * currentTemperature(xIndex, yIndex) + currentTemperature(xIndex, yIndex - 1)) / gridSpacingYSquared)
        NEXT yIndex
    NEXT xIndex
END SUB
