#include <stdio.h>

float put_premium_spot(int Buy_Put, int Sell_Put, float premium, float lot_size){
  float premium_paid = 0.0;
  if (Buy_Put > 0) {
    int i = 0;
    for (i=1; i<=Buy_Put; i++) {
        premium_paid = premium_paid - (premium * lot_size);
    }
  } else {
    int i = 0;
    for (i=1; i<=Sell_Put; i++) {
        premium_paid = premium_paid + (premium * lot_size);
    }
  }
  return premium_paid;
}

float call_premium_spot(int Buy_Call, int Sell_Call, float premium, float lot_size){
  float premium_paid = 0.0;
  if (Buy_Call > 0) {
    int i;
    for (i=1; i<=Buy_Call; i++) {
        premium_paid = premium_paid - (premium * lot_size);
    }
  } else {
    int i;
    for (i=1; i<=Sell_Call; i++) {
        premium_paid = premium_paid + (premium * lot_size);
    }
  }
  return premium_paid;
}

float call_premium(int Buy_Call, int Sell_Call, float spot_price, float strike_price, float premium, float lot_size)
{
  float max_return = 0.0;
  if (Buy_Call > 0) {
    int i = 0;
    for (i=1; i<=Buy_Call; i++) {
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
    for (i=1; i<=Sell_Call; i++) {
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
    for (i=1; i<=Buy_Put; i++) {
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
    for (i=1; i<=Sell_Put; i++) {
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

float new_max_return(float max_return, float old_max_return) {
  float new_max_return_val = max_return + old_max_return;
  return new_max_return_val;
}

float premium_paid(float premium_paid, float new_premium_paid) {
  float premium_paid_val = premium_paid + new_premium_paid;
  return premium_paid_val;
}

float main(void)
{
  return 0.0;
}

float max_loss_numerical_graph(float max_loss_numerical) {
  if (max_loss_numerical < 0) {
    float max_loss_numerical_graph_val = max_loss_numerical - ((40 * (-max_loss_numerical)) / 100.0);
    return max_loss_numerical_graph_val;
  } else {
    float max_loss_numerical_graph_val = max_loss_numerical - ((40 * max_loss_numerical) / 100.0);
    return max_loss_numerical_graph_val;
  }
}

float max_profit_numerical_graph(float max_profit_numerical) {
  float max_profit_numerical_graph_val = max_profit_numerical + ((40 * max_profit_numerical) / 100.0);
  return max_profit_numerical_graph_val;
}