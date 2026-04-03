program TwoDimensionalDiffusion;

const
  plateWidth = 10.0;
  plateHeight = 10.0;
  gridSpacingX = 0.1;
  gridSpacingY = 0.1;
  thermalDiffusivity = 4.0;

  coolTemperature = 300.0;
  hotTemperature = 700.0;

  numPointsX = 100;
  numPointsY = 100;

  gridSpacingXSquared = gridSpacingX * gridSpacingX;
  gridSpacingYSquared = gridSpacingY * gridSpacingY;
  timeStep = (gridSpacingXSquared * gridSpacingYSquared) /
    (2.0 * thermalDiffusivity * (gridSpacingXSquared + gridSpacingYSquared));

  hotRadius = 2.0;
  hotCentreX = 5.0;
  hotCentreY = 5.0;
  hotRadiusSquared = hotRadius * hotRadius;

  numTimeSteps = 101;

type
  TemperatureGrid = array[1..numPointsX, 1..numPointsY] of Double;

var
  currentTemperature: TemperatureGrid;
  nextTemperature: TemperatureGrid;
  stepNumber: Integer;

procedure SetInitialTemperature(var temperature: TemperatureGrid);
var
  xIndex, yIndex: Integer;
  xPosition, yPosition, distanceSquared: Double;
begin
  for xIndex := 1 to numPointsX do
  begin
    xPosition := (xIndex - 1) * gridSpacingX;
    for yIndex := 1 to numPointsY do
    begin
      yPosition := (yIndex - 1) * gridSpacingY;
      temperature[xIndex, yIndex] := coolTemperature;

      distanceSquared := Sqr(xPosition - hotCentreX) + Sqr(yPosition - hotCentreY);
      if distanceSquared < hotRadiusSquared then
        temperature[xIndex, yIndex] := hotTemperature;
    end;
  end;
end;

procedure CopyGrid(const source: TemperatureGrid; var destination: TemperatureGrid);
var
  xIndex, yIndex: Integer;
begin
  for xIndex := 1 to numPointsX do
    for yIndex := 1 to numPointsY do
      destination[xIndex, yIndex] := source[xIndex, yIndex];
end;

procedure DoTimeStep(const currentTemperature: TemperatureGrid; var nextTemperature: TemperatureGrid);
var
  xIndex, yIndex: Integer;
begin
  CopyGrid(currentTemperature, nextTemperature);

  for xIndex := 2 to numPointsX - 1 do
  begin
    for yIndex := 2 to numPointsY - 1 do
    begin
      nextTemperature[xIndex, yIndex] := currentTemperature[xIndex, yIndex] +
        thermalDiffusivity * timeStep *
        (
          (currentTemperature[xIndex + 1, yIndex] - 2.0 * currentTemperature[xIndex, yIndex] +
           currentTemperature[xIndex - 1, yIndex]) / gridSpacingXSquared
          +
          (currentTemperature[xIndex, yIndex + 1] - 2.0 * currentTemperature[xIndex, yIndex] +
           currentTemperature[xIndex, yIndex - 1]) / gridSpacingYSquared
        );
    end;
  end;
end;

begin
  SetInitialTemperature(currentTemperature);
  CopyGrid(currentTemperature, nextTemperature);

  Writeln('Step    Time (ms)    Centre temperature (K)');
  for stepNumber := 0 to numTimeSteps - 1 do
  begin
    DoTimeStep(currentTemperature, nextTemperature);
    CopyGrid(nextTemperature, currentTemperature);

    if (stepNumber = 0) or (stepNumber = 10) or (stepNumber = 50) or (stepNumber = 100) then
      Writeln(stepNumber:4, (stepNumber * timeStep * 1000.0):12:3,
        currentTemperature[numPointsX div 2, numPointsY div 2]:18:3);
  end;
end.
