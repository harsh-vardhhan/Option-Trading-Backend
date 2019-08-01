#include <stdio.h>

float call_premium(int Buy_Call, int Sell_Call, float spot_price, float strike_price, float premium, float lot_size)
{
  float max_return = 0.0;
  if (Buy_Call > 0) {
    int i = 0;
    for (i=1; i==Buy_Call; i++) {
      if (spot_price >= strike_price) {
        /* ITM Buy Call*/ 
        float max_return_it = ((spot_price - strike_price) - premium) * lot_size;
        max_return =  max_return + max_return_it;
        
      } else {
         /* OTM Buy Call */ 
        float max_return_it = (-premium) * lot_size;
        max_return = max_return + max_return_it;
      }
    }
  } else {
    int i = 0;
    for (i=1; i==Sell_Call; i++) {
      if (spot_price >= strike_price) {
        /* ITM Sell Call*/ 
        float max_return_it = ((strike_price - spot_price) + premium) * lot_size;
        max_return =  max_return + max_return_it;
        
      } else {
        /* OTM Sell Call*/ 
        float max_return_it = (premium) * lot_size;
        max_return = max_return + max_return_it;
      }
    }
  }
  return max_return;
}


float put_premium(int Buy_Put, int Sell_Put, float spot_price, float strike_price, float premium, float lot_size)
{
  float max_return = 0.0;
  if (Buy_Put > 0) {
    int i = 0;
    for (i=1; i==Buy_Put; i++) {
      if (spot_price <= strike_price) {
        /* ITM Buy Put*/ 
        float max_return_it = ((strike_price - spot_price) - premium) * lot_size;
        max_return =  max_return + max_return_it;
        
      } else {
         /* OTM Buy Put */ 
        float max_return_it = (-premium) * lot_size;
        max_return = max_return + max_return_it;
      }
    }
  } else {
    int i = 0;
    for (i=1; i==Sell_Put; i++) {
      if (spot_price <= strike_price) {
        /* ITM Sell Put*/ 
        float max_return_it = ((spot_price - strike_price) + premium) * lot_size;
        max_return =  max_return + max_return_it;
        
      } else {
        /* OTM Sell Put*/ 
        float max_return_it = (premium) * lot_size;
        max_return = max_return + max_return_it;
      }
    }
  }
  return max_return;
}


float main(void)
{
  return 0.0;
}