# Plain R logistic-regression script for the bar-profiles paper.

script_path <- tryCatch(normalizePath(sys.frame(1)$ofile), error = function(e) NA)
if (is.na(script_path)) {
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- "--file="
  script_path <- sub(file_arg, "", args[startsWith(args, file_arg)][1])
}
project_dir <- if (!is.na(script_path)) dirname(normalizePath(script_path)) else getwd()
basedir <- file.path(project_dir, "data")

read_if_exists <- function(filename) {
  path <- file.path(basedir, filename)
  if (!file.exists(path)) {
    message("Skipping missing table: ", path)
    return(NULL)
  }
  read.table(path, header=TRUE)
}

summarize_fit <- function(formula, data) {
  if (is.null(data)) {
    return(NULL)
  }
  fit <- glm(formula, family = binomial, data = data)
  print(summary(fit))
  fit
}

# %% Cell 5
basedir

# %% Cell 6
getwd()

# %% Cell 11
theTable_profs1 <- read_if_exists("PSh_profile-vs-stuff.dat")

# %% Cell 13
thefit1a <- summarize_fit(PSh_profile_both ~ logMstar, theTable_profs1)
thefit1b <- summarize_fit(PSh_profile_both ~ t_leda, theTable_profs1)
thefit1c <- summarize_fit(PSh_profile_both ~ logfgas, theTable_profs1)

# %% Cell 17
theTable_profs2 <- read_if_exists("PSh_profile-vs-stuff_modinc.dat")

# %% Cell 19
thefit2a <- summarize_fit(PSh_profile_both ~ logVrot, theTable_profs2)
thefit2b <- summarize_fit(PSh_profile_both ~ logMstar, theTable_profs2)
thefit2c <- summarize_fit(PSh_profile_both ~ t_leda, theTable_profs2)
thefit2d <- summarize_fit(PSh_profile_both ~ logfgas, theTable_profs2)

# %% Cell 21
theTable_profs4 <- read_if_exists("PSh_profile-vs-stuff_gmr_modinc.dat")

# %% Cell 23
thefit4a <- summarize_fit(PSh_profile_both ~ logMstar, theTable_profs4)
thefit4b <- summarize_fit(PSh_profile_both ~ t_leda, theTable_profs4)
thefit4c <- summarize_fit(PSh_profile_both ~ logfgas, theTable_profs4)
thefit4d <- summarize_fit(PSh_profile_both ~ gmr_sga_tc, theTable_profs4)

# %% Cell 25
theTable_profs3 <- read_if_exists("PSh_profile-vs-stuff_gmr+a2max.dat")

# %% Cell 27
thefit3a <- summarize_fit(PSh_profile_both ~ logMstar, theTable_profs3)
thefit3b <- summarize_fit(PSh_profile_both ~ t_leda, theTable_profs3)
thefit3c <- summarize_fit(PSh_profile_both ~ logfgas, theTable_profs3)
thefit3d <- summarize_fit(PSh_profile_both ~ gmr_sga_tc, theTable_profs3)
thefit3e <- summarize_fit(PSh_profile_both ~ A2_max, theTable_profs3)

# %% Cell 30
theTable_bp <- read_if_exists("bp_morph-vs-logmstar-logmbaryon-logvrot_modinc.dat")

thefit_bp_mstar <- summarize_fit(bp_morph ~ logMstar, theTable_bp)
thefit_bp_vrot <- summarize_fit(bp_morph ~ logVrot, theTable_bp)
