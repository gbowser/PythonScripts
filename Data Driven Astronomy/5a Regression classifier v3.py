import numpy as np
from sklearn.tree import DecisionTreeRegressor

# copy in your get_features_targets function here
def get_features_targets(data):
  # complete this function
    features = np.zeros((data.shape[0], 4))
        
    features[:, 0] = data['u'] - data['g']
    features[:, 1] = data['g'] - data['r']
    features[:, 2] = data['r'] - data['i']
    features[:, 3] = data['i'] - data['z']

    targets = np.zeros(data.shape[0])
    targets = data['redshift']

    return (features,targets)


def median_diff(predicted, actual):
  result=np.median(np.abs(predicted[:] - actual[:]))
  return result


# write a function that splits the data into training and testing subsets
# trains the model and returns the prediction accuracy with median_diff

def validate_model(model, features, targets):
   # split the data into training and testing
    split = 2*features.shape[0]//3
    train_features, test_features = features[:split], features[split:]
    train_targets, test_targets = targets[:split], targets[split:]

    # train the model
    model.fit(train_features, train_targets)

    # get the predicted_redshifts
    predictions = model.predict(test_features)  

    # use median_diff function to calculate the accuracy
    return median_diff(test_targets, predictions)


if __name__ == "__main__":
  data = np.load('sdss_galaxy_colors.npy')
  features, targets = get_features_targets(data)

  # initialize model
  dtr = DecisionTreeRegressor()

  # validate the model and print the med_diff
  diff = validate_model(dtr, features, targets)
  print('Median difference: {:f}'.format(diff))