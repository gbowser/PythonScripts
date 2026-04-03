program two_dimensional_diffusion
    implicit none

    ! Physical size of the square metal plate, in millimetres.
    real(8), parameter :: plate_width = 10.0d0
    real(8), parameter :: plate_height = 10.0d0

    ! Distance between neighbouring grid points in the x and y directions.
    real(8), parameter :: grid_spacing_x = 0.1d0
    real(8), parameter :: grid_spacing_y = 0.1d0

    ! Thermal diffusivity of steel, in mm^2 s^-1.
    real(8), parameter :: thermal_diffusivity = 4.0d0

    ! Background and hot-spot temperatures, in kelvin.
    real(8), parameter :: cool_temperature = 300.0d0
    real(8), parameter :: hot_temperature = 700.0d0

    ! Number of grid points used to represent the plate.
    integer, parameter :: num_points_x = int(plate_width / grid_spacing_x)
    integer, parameter :: num_points_y = int(plate_height / grid_spacing_y)

    ! Precompute repeated terms used in the diffusion update.
    real(8), parameter :: grid_spacing_x_squared = grid_spacing_x * grid_spacing_x
    real(8), parameter :: grid_spacing_y_squared = grid_spacing_y * grid_spacing_y

    ! Choose a stable time step for the explicit finite-difference scheme.
    real(8), parameter :: time_step = (grid_spacing_x_squared * grid_spacing_y_squared) / &
        (2.0d0 * thermal_diffusivity * (grid_spacing_x_squared + grid_spacing_y_squared))

    ! Initial hot circular patch centred on the plate.
    real(8), parameter :: hot_radius = 2.0d0
    real(8), parameter :: hot_centre_x = 5.0d0
    real(8), parameter :: hot_centre_y = 5.0d0
    real(8), parameter :: hot_radius_squared = hot_radius * hot_radius

    ! Total number of time steps to simulate.
    integer, parameter :: num_time_steps = 101

    real(8), dimension(num_points_x, num_points_y) :: current_temperature
    real(8), dimension(num_points_x, num_points_y) :: next_temperature
    real(8) :: x_position, y_position, distance_squared
    integer :: x_index, y_index, step_number

    call set_initial_temperature(current_temperature)
    next_temperature = current_temperature

    print '(a)', 'Step    Time (ms)    Centre temperature (K)'
    do step_number = 0, num_time_steps - 1
        call do_timestep(current_temperature, next_temperature)
        current_temperature = next_temperature

        if (step_number == 0 .or. step_number == 10 .or. step_number == 50 .or. step_number == 100) then
            print '(i4, 4x, f8.3, 8x, f10.3)', step_number, step_number * time_step * 1000.0d0, &
                current_temperature(num_points_x / 2, num_points_y / 2)
        end if
    end do

contains

    subroutine set_initial_temperature(temperature)
        implicit none
        real(8), intent(out), dimension(num_points_x, num_points_y) :: temperature

        temperature = cool_temperature

        do x_index = 1, num_points_x
            x_position = (x_index - 1) * grid_spacing_x
            do y_index = 1, num_points_y
                y_position = (y_index - 1) * grid_spacing_y
                distance_squared = (x_position - hot_centre_x) ** 2 + (y_position - hot_centre_y) ** 2

                if (distance_squared < hot_radius_squared) then
                    temperature(x_index, y_index) = hot_temperature
                end if
            end do
        end do
    end subroutine set_initial_temperature

    subroutine do_timestep(current_temperature, next_temperature)
        implicit none
        real(8), intent(in), dimension(num_points_x, num_points_y) :: current_temperature
        real(8), intent(out), dimension(num_points_x, num_points_y) :: next_temperature

        ! Start from the current field so the edges remain unchanged.
        next_temperature = current_temperature

        ! Update only the interior points using the four nearest neighbours:
        ! above, below, left, and right.
        do x_index = 2, num_points_x - 1
            do y_index = 2, num_points_y - 1
                next_temperature(x_index, y_index) = current_temperature(x_index, y_index) + &
                    thermal_diffusivity * time_step * ( &
                    (current_temperature(x_index + 1, y_index) - 2.0d0 * current_temperature(x_index, y_index) + &
                     current_temperature(x_index - 1, y_index)) / grid_spacing_x_squared + &
                    (current_temperature(x_index, y_index + 1) - 2.0d0 * current_temperature(x_index, y_index) + &
                     current_temperature(x_index, y_index - 1)) / grid_spacing_y_squared )
            end do
        end do
    end subroutine do_timestep

end program two_dimensional_diffusion
