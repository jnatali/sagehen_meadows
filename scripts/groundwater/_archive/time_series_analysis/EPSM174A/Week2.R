### ESPM 174A, Fall 2020
## Week 2 - Aug 31 & Sept 2, 2020
library(astsa)

## Code chunk 2.1
set.seed(1)
nn <- 50
tt <- 40
ww <- matrix(rnorm(nn*tt), tt, nn)
par(mai = c(0.9,0.9,0.1,0.1), omi = c(0,0,0,0))
matplot(ww, type="l", lty="solid",  las = 1,
        ylab = expression(italic(X[t])), xlab = "Time",
        col = gray(0.5, 0.4))
lines(ww[,1], col = "blue", lwd = 2)
lines(ww[,2], col = "red", lwd = 2)
lines(ww[,3], col = "green", lwd = 2)

## Code chunk 2.2: decomposition exercise
# Load data set: number of births per month in NY
births <- scan("http://robjhyndman.com/tsdldata/data/nybirths.dat")
head(births) # this is just a vector
births <- ts(births, frequency = 12, start = c(1946, 1)) # let's convert it into a time series
str(births) # OK
plot.ts(births) # Looks good
# Decompose manually: extract trend using linear filter
originalseries = births
ma3 = stats::filter(originalseries, sides=2, rep(1/3,3)) # moving average
ma9 = stats::filter(originalseries, sides=2, rep(1/9,9)) # moving average
par(mfrow=c(3,1))
plot.ts(originalseries, main="original series")
plot.ts(ma3, main="moving average 1/3, 3")
plot.ts(ma9, main="moving average 1/9, 9") # see that as the denominator increases, the resulting series shrinks
# Decompose 'automatically', using decompose()
birthsComp <- decompose(births)
birthsComp # see there is a trend component, a seasonal component, and a random component 'noise'
str(birthsComp)
plot(birthsComp)
# Show data adjusted by seasonality
birthsSeasonAdj <- births - birthsComp$seasonal
plot.ts(birthsSeasonAdj) # this reflects the trend + random component
plot.ts(births) # compare to original data
plot.ts(birthsComp$seasonal) # what we substracted from the original data

## Code chunk 2.3: White Noise (WN) with different sigmas
set.seed(1)
w1 = rnorm(100,0,1) # 100 N(0,1) variates with mean 0, variance 1
plot.ts(w1, main="white noise, sigma2=1", ylim=c(-2,2))
w2 = rnorm(100,0,0.5) # 100 N(0,0.5) variates with mean 0, variance 0.5
plot.ts(w2, main="white noise, sigma2=1", ylim=c(-2,2))
w3 = rnorm(100,0,0.1) # 100 N(0,0.5) variates with mean 0, variance 0.1
plot.ts(w3, main="white noise, sigma2=0.1", ylim=c(-2,2))
w4 = rnorm(100,1,0.1) # 100 N(0,0.5) variates with mean 1, variance 0.1
plot.ts(w4, main="white noise, mean=1, sigma2=0.1", ylim=c(-2,2))

## Code chunk 2.4: White Noise (WN) and moving averages
w = rnorm(100,0,1) # 100 N(0,1) variates
v3 = stats::filter(w, sides=2, rep(1/3,3)) # moving average
v9 = stats::filter(w, sides=2, rep(1/9,9)) # moving average
par(mfrow=c(3,1))
plot.ts(w, main="white noise")
plot.ts(v3, ylim=c(-3,3), main="moving average 1/3, 3")
plot.ts(v9, ylim=c(-3,3), main="moving average 1/9, 9")

## Code chunk 2.4: Random Walk (RW)
par(mfrow=c(3,1))
w1 = rnorm(100,0,1); cumsum_w1<-cumsum(w1)
plot.ts(cumsum_w1,main="Random walk 1")
w2 = rnorm(100,0,1); cumsum_w2<-cumsum(w2)
plot.ts(cumsum_w2,main="Random walk 2")
w3 = rnorm(100,0,1); cumsum_w3<-cumsum(w3)
plot.ts(cumsum_w3,main="Random walk 3")

# Code 2.5: ACF on White Noise ts
par(mfrow=c(2,1))
white.noise = rnorm(100,0,1)
plot.ts(white.noise,main="White Noise")
acf(white.noise)

# Code 2.6: ACF on Random Walk ts
par(mfrow=c(2,1))
w1 = rnorm(100,0,1); RW<-cumsum(w1)
plot.ts(RW,main="Random Walk")
acf(RW)

# Code 2.7: ACF on RW w/ positive drift
par(mfrow=c(2,1))
w1 = rnorm(100,0,1); RWposdrift<-cumsum(w1+0.1)
plot.ts(RWposdrift,main="RW with positive drift")
acf(RWposdrift)

# Code 2.8: ACF on RW w/ negative drift
par(mfrow=c(2,1))
w1 = rnorm(100,0,1); RWnegdrift<-cumsum(w1-0.1)
plot.ts(RWnegdrift,main="RW with negative drift")
acf(RWnegdrift)

# Code 2.9: ACF on Periodic ts
par(mfrow=c(2,1))
periodic_ts = sin(seq(0,10*pi,length.out=100))+
  rnorm(100,0,1)
plot.ts(periodic_ts,main="Periodic ts")
acf(periodic_ts)

# Code 2.10: Exercise: guess the time series (based on the ACF)
par(mfrow=c(2,1))
w1 = rnorm(100,0,0.05); RWnegdrift<-cumsum(w1-0.05)
periodic_ts2 = 
  sin(seq(0,50*pi,length.out=100))+
  RWnegdrift
acf(periodic_ts2)
plot.ts(periodic_ts2,main="Periodic ts w/ negative drift")
# changing the sign of drift would have not fundamentally changed the ACF
w1 = rnorm(100,0,0.05); RWnegdrift<-cumsum(w1+0.05)
periodic_ts3 = 
  sin(seq(0,50*pi,length.out=100))+
  RWnegdrift
acf(periodic_ts3)
plot.ts(periodic_ts3,main="Periodic ts w/ positive drift")

# Code 2.11: Partial autocorrelation function (PACF)
par(mfrow=c(3,1))
w1 = rnorm(100,0,0.05); RWnodrift<-cumsum(w1)
periodic_ts4 = 
  sin(seq(0,50*pi,length.out=100))+
  RWnodrift
plot.ts(periodic_ts4,main="Periodic ts")
acf(periodic_ts4)
pacf(periodic_ts4)

# Code 2.12: Two different AR(1) models with positive Phi
set.seed(1)
AR1.largecoef <- list(order = c(1, 0, 0), ar = 0.9, sd = 0.1) # AR(1) model with large coefficient
AR1.smallcoef <- list(order = c(1, 0, 0), ar = 0.1, sd = 0.1) # AR(1) model with small coefficient
# simulate AR(1)
AR1large <- arima.sim(n = 50, model = AR1.largecoef)
AR1small <- arima.sim(n = 50, model = AR1.smallcoef)
# plot
par(mfrow = c(2, 1))
## plot the ts
plot.ts(AR1large, ylim = c(-8,8), ylab = expression(italic(x)[italic(t)]), 
        main = expression(paste(phi, " = 0.9")))
plot.ts(AR1small, ylim = c(-8,8), ylab = expression(italic(x)[italic(t)]), 
        main = expression(paste(phi, " = 0.1")))

# Code 2.13: Two different AR(1) models with negative Phi
set.seed(1)
AR1.largecoef <- list(order = c(1, 0, 0), ar = -0.9, sd = 0.1) # AR(1) model with large (negative) coefficient
AR1.smallcoef <- list(order = c(1, 0, 0), ar = -0.1, sd = 0.1) # AR(1) model with small (negative) coefficient
# simulate AR(1)
AR1large <- arima.sim(n = 50, model = AR1.largecoef)
AR1small <- arima.sim(n = 50, model = AR1.smallcoef)
# plot
par(mfrow = c(2, 1))
## plot the ts
plot.ts(AR1large, ylim = c(-8,8), ylab = expression(italic(x)[italic(t)]), 
        main = expression(paste(phi, " = -0.9")))
plot.ts(AR1small, ylim = c(-8,8), ylab = expression(italic(x)[italic(t)]), 
        main = expression(paste(phi, " = -0.1")))

# Code 2.14: Variance, covariance
set.seed(10)
data1<-rnorm(100, 0,1); var(data1)
data2<-rnorm(100, 0,1); var(data2)
var(data1)
var(data2)
print(varcovmatrix<-cov(cbind(data1,data2))) # variance in the diagonal, covariance in the off-diagonal
cov2cor(varcovmatrix) # We scaled the covariance matrix into a correlation one 

# Code 2.15: Pearson, Spearman, Kendall correlation
cor(data1,data2, method="pearson") # Note that the off-diagonal values are the Pearson's correlation coefficients from 2.14
cor(data1,data2, method="spearman") # This is Spearman (Rho) rank correlation
cor(data1,data2, method="kendall") # This is Kendall's (Tau) rank correlation--generally yields lower value than Spearman

# Code 2.16: Man-Kendall Theil-Sen
library(openair)
data(mydata) # load data
str(mydata) # explore pollutant data
TheilSen(mydata, pollutant = "o3", ylab = "o3 (ppb)", alpha = 0.01) # trend plot for ozone

# Code 2.17: Breakpoint analysis
# Nile data with one breakpoint: the annual flows drop in 1898 
# because the first Ashwan dam was built
library(strucchange)
data("Nile")
par(mfrow = c(2, 1))
plot(Nile)
fs.nile <- Fstats(Nile ~ 1) ## F statistics indicate one breakpoint
plot(fs.nile)
breakpoints(fs.nile)
lines(breakpoints(fs.nile))

# Code 2.18: Breakpoint--assessing partitionings, CI
bp.nile <- breakpoints(Nile ~ 1)
summary(bp.nile)
fm0 <- lm(Nile ~ 1) ## fit null hypothesis model and model with 1 breakpoint
fm1 <- lm(Nile ~ breakfactor(bp.nile, breaks = 1))
lines(ts(fitted(fm0), start = 1871), col = 3)
lines(ts(fitted(fm1), start = 1871), col = 4)
lines(bp.nile)
print(ci.nile <- confint(bp.nile)) # confidence interval (CI)
lines(ci.nile)

# Code 2.19: Let's try detect structural change in an AR(1)
set.seed(10)
years = 40 # 40 years simulated here
sigma = 1 # High variability
Phi = 0.9 # This will be the AR coefficient
w = rnorm(years, 0,sigma) # Create vector of white noise ~ Normal(mean,sd)
x = 0 # initial value, it starts being permanent
for(t in 2:years) {x[t] = Phi*x[t-1] + w[t]}
x<-as.ts(x)
plot(x, main = "An AR(1) with Phi=0.9")
# Code 2.19 (cont): Let's try detect structural change in an AR(1)
par(mfrow = c(2, 1))
bp.x <- breakpoints(x ~ 1) # breakpoints
summary(bp.x); plot(bp.x) # it seems 2 breakpoints is optimal according to BIC
print(breakpoint.results<-breakpoints(bp.x)) # this is the location of the breakpoints
print(n.breakpoints<-length(breakpoint.results$breakpoints)) # we store the optimal number of breakpoints
# fit and plot model with breakpoints
fm1 <- lm(x ~ breakfactor(bp.x, breaks = n.breakpoints))
plot(x)
lines(ts(fitted(fm1)), col=2) # show breakpoints
lines(ci.x <- confint(bp.x)) # show breakpoint confidence intervals

## End