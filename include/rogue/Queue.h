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
#include <boost/thread/mutex.hpp>
#include <boost/thread/condition_variable.hpp>
#include <queue>

namespace rogue {
   template<typename T> 
   class Queue {
      private:
          std::queue<T> queue_;
          mutable boost::mutex mtx_;
          boost::condition_variable pushCond_;
          boost::condition_variable popCond_;
          uint32_t max_;
      public:

          Queue() { max_ = 0; }

          void setMax(uint32_t max) { max_ = max; }

          void push(T const &data) {
             boost::mutex::scoped_lock lock(mtx_);
   
             while(max_ > 0 && queue_.size() >= max_) 
                pushCond_.wait(lock);

             queue_.push(data);
             lock.unlock();
             popCond_.notify_all();
          }

          bool empty() {
             boost::mutex::scoped_lock lock(mtx_);
             return queue_.empty();
          }

          uint32_t size() {
             boost::mutex::scoped_lock lock(mtx_);
             return queue_.size();
          }

          void reset() {
             boost::mutex::scoped_lock lock(mtx_);
             while(!queue_.empty()) queue_.pop();
             lock.unlock();
             pushCond_.notify_all();
          }

          T pop() {
             T ret;
             boost::mutex::scoped_lock lock(mtx_);
             while(queue_.empty()) popCond_.wait(lock);
             ret=queue_.front();
             queue_.pop();
             lock.unlock();
             pushCond_.notify_all();
             return(ret);
          }

   }; 
}

#endif
