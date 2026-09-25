#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""Apply identical probes to an exported Rogue tree; fail on unfamiliar code."""
from pathlib import Path
import sys


def instrument(root, timer_locks=True):
    def edit(rel, changes):
        path = root / rel
        text = path.read_text()
        for old, new, count in changes:
            if text.count(old) != count:
                raise RuntimeError(f'{rel}: expected {count} occurrences of {old!r}, got {text.count(old)}')
            text = text.replace(old, new)
        path.write_text('#include "Trace.h"\n' + text)

    edit('include/rogue/Queue.h', [
        ('while (run_ && max_ > 0 && queue_.size() >= max_) pushCond_.wait(lock);',
         'while (run_ && max_ > 0 && queue_.size() >= max_) {\n'
         '            burst::emit("queue_full_wait_begin", this, queue_.size(), max_);\n'
         '            pushCond_.wait(lock);\n'
         '            burst::emit("queue_full_wait_end", this, queue_.size(), max_);\n        }', 1),
        ('busy_ = (thold_ > 0 && queue_.size() >= thold_);\n        popCond_.notify_all();', 'busy_ = (thold_ > 0 && queue_.size() >= thold_);\n        burst::emit("queue_push", this, queue_.size(), busy_);\n        popCond_.notify_all();', 1),
        ('return (ret);', 'burst::emit("queue_pop", this, queue_.size(), busy_);\n        return (ret);', 1),
    ])
    edit('src/rogue/protocols/rssi/Application.cpp', [
        ('if ((frame = cntl_->applicationTx()) != NULL) sendFrame(frame);',
         'if ((frame = cntl_->applicationTx()) != NULL) {\n'
         '            burst::Scope scope("rssi_callback", this);\n'
         '            burst::stall("app", this);\n            sendFrame(frame);\n        }', 1),
    ])
    edit('src/rogue/protocols/rssi/Controller.cpp', [
        ('appQueue_.setThold(2);', 'appQueue_.setThold(2);\n    burst::emit("rssi_queue", this, reinterpret_cast<uintptr_t>(&appQueue_), server_);', 1),
        ('// Ack set', 'burst::emit("rssi_rx", this, head->sequence, head->acknowledge,\n'
         '                head->busy | (head->rst << 1) | (head->syn << 2) | (head->nul << 3));\n    // Ack set', 1),
        ('// Check for busy state transition', 'burst::emit("ack_rx", this, lastAckRx_);\n    // Check for busy state transition', 1),
        ('ackSeqRx_ = head->sequence;', 'ackSeqRx_ = head->sequence;\n        burst::emit("rssi_dequeue", this, head->sequence, head->nul);', 1),
        ('void rpr::Controller::applicationRx(ris::FramePtr frame) {',
         'void rpr::Controller::applicationRx(ris::FramePtr frame) {\n'
         '    burst::Scope scope("rssi_send", this);\n'
         '    burst::stall("tx", app_.get());', 1),
        ('// Wait while busy either by flow control or buffer starvation',
         'burst::Scope windowScope("rssi_window_wait", this);\n'
         '    burst::emit("rssi_window_enter", this, txListCount_, curMaxBuffers_);\n    // Wait while busy either by flow control or buffer starvation', 1),
        ('// Transmit\n    transportTx(head, true, false);',
         'burst::emit("rssi_window_ready", this, txListCount_, curMaxBuffers_);\n    // Transmit\n    transportTx(head, true, false);', 1),
        ('locBusy_ = queueBusy;', 'if (locBusy_ != queueBusy) burst::emit("local_busy", this, queueBusy);\n    locBusy_ = queueBusy;', 1),
        ('head->update();', 'head->update();\n    burst::emit("rssi_tx", this, head->sequence, head->acknowledge,\n'
         '                head->busy | (head->rst << 1) | (head->syn << 2) | (head->nul << 3));', 2),
        ('retranCount_++;', 'retranCount_++;\n    burst::emit("retransmit", this, id, head->count());', 1),
        ('if (head->count() >= curMaxRetran_) return -1;',
         'if (head->count() >= curMaxRetran_) { burst::emit("reset_retry_limit", this, id); return -1; }', 1),
        ('if ((head->rst) || (head->syn && (!head->ack))) {',
         'if ((head->rst) || (head->syn && (!head->ack))) {\n            burst::emit("reset_peer", this, head->rst);', 1),
        ('// Send reset on exit', 'burst::emit("reset_shutdown", this);\n    // Send reset on exit', 1),
        ('struct timeval& rpr::Controller::stateError() {',
         'struct timeval& rpr::Controller::stateError() {\n    burst::emit("reset", this);', 1),
    ])
    edit('src/rogue/protocols/packetizer/Controller.cpp', [
        ('tranQueue_.setThold(64);',
         'const unsigned peerLimit = burst::constructingPeer ? burst::envUnsigned("BURST_PEER_RESPONSES", 0) : 0;\n'
         '    tranQueue_.setThold(peerLimit ? peerLimit : 64);\n'
         '    tranQueue_.setMax(peerLimit);\n'
         '    burst::emit("packet_tx_queue", this, reinterpret_cast<uintptr_t>(&tranQueue_), peerLimit, burst::constructingPeer);', 1),
    ])
    edit('src/rogue/protocols/srp/SrpV3Emulation.cpp', [
        ('std::lock_guard<std::mutex> lock(queMtx_);\n        queue_.push(frame);',
         'rogue::GilRelease noGil;\n'
         '        std::unique_lock<std::mutex> lock(queMtx_);\n'
         '        const unsigned limit = burst::envUnsigned("BURST_PEER_REQUESTS", 0);\n'
         '        while (threadEn_ && limit && queue_.size() >= limit) {\n'
         '            burst::emit("peer_request_wait_begin", this, queue_.size(), limit);\n'
         '            queCond_.wait(lock);\n'
         '            burst::emit("peer_request_wait_end", this, queue_.size(), limit);\n'
         '        }\n'
         '        if (!threadEn_) return;\n'
         '        queue_.push(frame);\n'
         '        burst::emit("peer_request_push", this, queue_.size(), limit);', 1),
        ('queue_.pop();', 'queue_.pop();\n'
         '            burst::emit("peer_request_pop", this, queue_.size());\n'
         '            queCond_.notify_all();', 1),
        ('void rps::SrpV3Emulation::processFrame(ris::FramePtr frame) {',
         'void rps::SrpV3Emulation::processFrame(ris::FramePtr frame) {\n'
         '    burst::Scope scope("peer_process", this);', 1),
    ])
    edit('src/rogue/protocols/packetizer/Application.cpp', [
        ('queue_.setMax(8);', 'queue_.setMax(8);\n    burst::emit("packet_app_queue", this, reinterpret_cast<uintptr_t>(&queue_), id_);', 1),
        ('queue_.push(frame);', 'burst::Scope scope("packet_app_push", this);\n    queue_.push(frame);', 1),
        ('if ((frame = queue_.pop()) != NULL) sendFrame(frame);',
         'if ((frame = queue_.pop()) != NULL) {\n'
         '            burst::Scope scope("packet_app_callback", this);\n'
         '            sendFrame(frame);\n        }', 1),
    ])
    edit('src/rogue/protocols/packetizer/ControllerV2.cpp', [
        ('void rpp::ControllerV2::transportRx(ris::FramePtr frame) {',
         'void rpp::ControllerV2::transportRx(ris::FramePtr frame) {\n    burst::Scope scope("packet_rx", this);', 1),
        ('void rpp::ControllerV2::applicationRx(ris::FramePtr frame, uint8_t tDest) {',
         'void rpp::ControllerV2::applicationRx(ris::FramePtr frame, uint8_t tDest) {\n    burst::Scope scope("packet_send", this);', 1),
        ('// Wait while queue is busy', 'burst::emit("packet_queue_wait_begin", this);\n    // Wait while queue is busy', 1),
        ('fUser = frame->getFirstUser();', 'burst::emit("packet_queue_wait_end", this);\n    fUser = frame->getFirstUser();', 1),
        ('app_[tmpDest]->pushFrame(tranFrame_[tmpDest]);',
         'burst::Scope callback("packet_callback", this);\n            app_[tmpDest]->pushFrame(tranFrame_[tmpDest]);', 1),
    ])
    edit('src/rogue/protocols/srp/SrpV3.cpp', [
        ('void rps::SrpV3::doTransaction(rim::TransactionPtr tran) {',
         'void rps::SrpV3::doTransaction(rim::TransactionPtr tran) {\n    burst::Scope scope("srp_submit", this);\n    burst::emit("srp_request", this, tran->id(), tran->size());', 1),
        ('sendFrame(frame);', 'sendFrame(frame);\n    burst::stall("submit", this);', 1),
        ('void rps::SrpV3::acceptFrame(ris::FramePtr frame) {',
         'void rps::SrpV3::acceptFrame(ris::FramePtr frame) {\n    burst::Scope scope("srp_callback", this);\n    burst::stall("srp", this);', 1),
        ('// Lock transaction', 'burst::emit("srp_response", this, id);\n    // Lock transaction', 1),
        ('    tran->done();\n}', '    tran->done();\n    burst::emit("srp_done", this, id);\n}', 1),
    ])
    if timer_locks:
        edit('src/rogue/interfaces/memory/Slave.cpp', [
            ('void rim::Slave::addTransaction(rim::TransactionPtr tran) {',
             'void rim::Slave::addTransaction(rim::TransactionPtr tran) {\n    burst::Scope scope("map_add", this);', 1),
            ('rim::TransactionPtr rim::Slave::getTransaction(uint32_t index) {',
             'rim::TransactionPtr rim::Slave::getTransaction(uint32_t index) {\n'
             '    burst::Scope scope("map_get", this);\n    burst::emit("map_lookup", this, index);', 1),
            ('std::lock_guard<std::mutex> lock(slaveMtx_);',
             'burst::emit("map_lock_wait", this);\n'
             '    std::lock_guard<std::mutex> lock(slaveMtx_);\n'
             '    burst::emit("map_lock_acquired", this);', 2),
        ])
        edit('src/rogue/interfaces/memory/Transaction.cpp', [
            ('void rim::Transaction::refreshTimer(rim::TransactionPtr ref) {',
             'void rim::Transaction::refreshTimer(rim::TransactionPtr ref) {\n'
             '    burst::emit("refresh_wait", this, id_, ref ? ref->id() : 0);', 1),
            ('std::lock_guard<std::mutex> lock(lock_);',
             'std::lock_guard<std::mutex> lock(lock_);\n'
             '    burst::emit("refresh_acquired", this, id_, ref ? ref->id() : 0);', 1),
        ])
    edit('src/rogue/interfaces/memory/TransactionLock.cpp', [
        ('    tran_->lock_.lock();', '    burst::emit("lock_wait", tran_.get(), tran_->id());\n'
         '    tran_->lock_.lock();\n    burst::emit("lock_acquired", tran_.get(), tran_->id());', 2),
        ('if (locked_) tran_->lock_.unlock();',
         'if (locked_) { burst::emit("lock_release", tran_.get(), tran_->id()); tran_->lock_.unlock(); }', 1),
    ])


if __name__ == '__main__':
    instrument(Path(sys.argv[1]))
