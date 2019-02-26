/**
 *-----------------------------------------------------------------------------
 * Title      : General Queue
 * ----------------------------------------------------------------------------
 * File       : Queue.h
 * Created    : 2017-01-18
 * ----------------------------------------------------------------------------
 * Description:
 * General queue for Rogue
 * ----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to 
 * the license terms in the LICENSE.txt file found in the top-level directory 
 * of this distribution and at: 
 *    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
 * No part of the rogue software platform, including this file, may be 
 * copied, modified, propagated, or distributed except according to the terms 
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
**/
#ifndef __ROGUE_QUEUE_H__
#define __ROGUE_QUEUE_H__
#include <condition_variable>
#include <stdint.h>
#include <queue>
#include <mutex>

namespace rogue {
   template<typename T> 
   class Queue {
      private:
          std::queue<T> queue_;
          mutable std::mutex mtx_;
          std::condition_variable pushCond_;
          std::condition_variable popCond_;
          uint32_t max_;
          uint32_t thold_;
          bool     busy_;
      public:

          Queue() { 
             max_   = 0; 
             thold_ = 0;
             busy_  = false;
          }

          void setMax(uint32_t max) { max_ = max; }

          void setThold(uint32_t thold) { thold_ = thold; }

          void push(T const &data) {
             std::unique_lock lock(mtx_);
   
             while(max_ > 0 && queue_.size() >= max_) 
                pushCond_.wait(lock);

             queue_.push(data);
             busy_ = ( thold_ > 0 && queue_.size() > thold_ );
             lock.unlock();
             popCond_.notify_all();
          }

          bool empty() {
             return queue_.empty();
          }

          uint32_t size() {
             std::scoped_lock lock(mtx_);
             return queue_.size();
          }

          bool busy() {
             return busy_;
          }

          void reset() {
             std::unique_lock lock(mtx_);
             while(!queue_.empty()) queue_.pop();
             busy_ = false;
             lock.unlock();
             pushCond_.notify_all();
          }

          T pop() {
             T ret;
             std::unique_lock lock(mtx_);
             while(queue_.empty()) popCond_.wait(lock);
             ret=queue_.front();
             queue_.pop();
             busy_ = ( thold_ > 0 && queue_.size() > thold_ );
             lock.unlock();
             pushCond_.notify_all();
             return(ret);
          }
   }; 
}

#endif
