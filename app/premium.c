#include <stdio.h>

float cal_premium(float spot_price, float strike_price, float premium, float lot_size)
{
    float final_premium = ((spot_price - strike_price) - premium) * lot_size;
    return final_premium;
}

float main(void)
{
  return 0.0;
}