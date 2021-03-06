from __future__ import division

from ..infer.backlash_compensator import BacklashCompensator
from ..infer.line_of_best_fit import line_of_best_fit


# A system for converting line positions on each side of the road to steering angles, using outlier detection and PID.
# Created by brendon-ai, September 2017


# Main class, instantiated with PID parameters and road edge weights
class PDSteeringEngine:
    # Line of best fit through the points on the center of the road, accessible to external scripts
    center_line_of_best_fit = None

    # A list containing the proportional and derivative errors, set after computation of the steering angle
    errors = None

    # Set global variables provided as arguments and initialize a backlash compensator
    def __init__(self, proportional_multiplier, derivative_multiplier,
                 max_distance_from_line, ideal_center_x, center_y,
                 steering_limit):

        # Positive multipliers for the proportional and derivative error terms calculated for steering
        self.proportional_multiplier = proportional_multiplier
        self.derivative_multiplier = derivative_multiplier

        # Distance off of the line of best fit a point must be to be considered an outlier
        self.max_distance_from_line = max_distance_from_line

        # Ideal horizontal position for the center of the road
        self.ideal_center_x = ideal_center_x

        # Vertical position at which the center of the road is calculated
        self.center_y = center_y

        # Maximum permitted absolute value for the steering angle
        self.steering_limit = steering_limit

        # Create a persistent backlash compensator
        self.backlash_compensator = BacklashCompensator()

    # Compute a steering angle, given points down the center of the road
    def compute_steering_angle(self, center_points):

        # If there are not at least two points, return None because there is no reasonable line of best fit
        if len(center_points) < 2:
            return None

        # Remove the outliers from the points and calculate the line of best fit
        self.remove_outliers(center_points)

        # Get the slope and intercept from the line of best fit
        line_intercept, line_slope = self.center_line_of_best_fit

        # Calculate two points on the line at the predefined high and low positions
        center_x = (self.center_y * line_slope) + line_intercept

        # Calculate the proportional error from the ideal center
        proportional_error = self.ideal_center_x - center_x

        # Set the public error list
        self.errors = [proportional_error, line_slope]

        # Multiply the error by the steering multiplier, and the slope of the line by the derivative multiplier
        steering_angle = (proportional_error * self.proportional_multiplier) + (line_slope * self.derivative_multiplier)

        # Compensate for backlash in the mechanism or simulator
        steering_angle = self.backlash_compensator.process(steering_angle)

        # If the steering angle is greater than the maximum, set it to the maximum
        if steering_angle > self.steering_limit:
            steering_angle = self.steering_limit

        # If it is less than the minimum, set it to the minimum
        elif steering_angle < -self.steering_limit:
            steering_angle = -self.steering_limit

        # Return the steering angle and the error
        return steering_angle, proportional_error, line_slope

    # Remove the outliers from a set of points given a line of best fit and a maximum directly horizontal distance
    # that a point can be away from the line in order to not be considered an outlier
    def remove_outliers(self, positions):

        # Make a copy of the provided list
        positions = list(positions)

        # A function to compute and store the line of best fit
        def store_line_of_best_fit():
            self.center_line_of_best_fit = line_of_best_fit(positions)

        # The previous value of the number of positions in the list
        previous_num_positions = None

        # Loop until no positions are removed any longer
        while len(positions) != previous_num_positions:

            # Update the previous number of positions before removing items
            previous_num_positions = len(positions)

            # Compute the line of best fit for the center line with the latest position list
            store_line_of_best_fit()

            # Keep track of the greatest horizontal distance from the line so far and its corresponding point
            greatest_distance_value = None
            greatest_distance_position = None

            # Iterate over a copy of the list of positions
            for position in list(positions):

                # Get the X and Y positions
                y_position = position[0]
                x_position = position[1]

                # Calculate the X position that lies on the line corresponding to the Y position of the current point
                predicted_x_position = (self.center_line_of_best_fit[1] * y_position) + self.center_line_of_best_fit[0]

                # If the distance between the predicted and actual X positions is greater than the greatest so far,
                # set the greatest distance variables to correspond to the current position
                current_distance = abs(predicted_x_position - x_position)
                if current_distance > greatest_distance_value:
                    greatest_distance_value = current_distance
                    greatest_distance_position = position

            # If the greatest distance is greater than the threshold, remove the corresponding point from the list
            if greatest_distance_value > self.max_distance_from_line:
                positions.remove(greatest_distance_position)

        # Update the line of best fit with the final points before exiting
        store_line_of_best_fit()

        # Return the copied list
        return positions
