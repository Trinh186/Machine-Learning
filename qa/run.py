"""RFM Insight QA: executable test matrix, safe by default.

Run from repository root: python -m qa.run
--db: read-only database checks; --gui: offscreen PyQt checks; --slow: costly dataset checks.
No command in this runner starts/stops MySQL, modifies production tables or exports into repo.
"""
from __future__ import annotations

import argparse
import ast
import csv
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import traceback
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / 'ui_app'
ML = ROOT / 'customer_segmentation'
for path in (str(UI), str(ML)):
    if path not in sys.path:
        sys.path.insert(0, path)


class NeedsEnvironment(Exception):
    """An honest SKIP when required local resources are unavailable."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def skip(reason: str) -> None:
    raise NeedsEnvironment(reason)


def optional_import(name: str):
    try:
        return __import__(name)
    except (ImportError, ModuleNotFoundError) as exc:
        skip(f'Thiếu thư viện {name}: {exc}; cài requirements.txt')


class QA:
    def __init__(self, args):
        self.args = args
        self._model = None
        self._auth = None
        self._db = None
        self._qapp = None
        self.results = {}

    def source(self, rel):
        return (ROOT / rel).read_text(encoding='utf-8-sig')

    def require_file(self, rel):
        p = ROOT / rel
        if not p.is_file():
            skip(f'Chưa có {rel}')
        return p

    def auth(self):
        optional_import('bcrypt')
        from auth.auth_service import AuthService, AuthenticationError, AuthorizationError
        import bcrypt

        class MemoryDAO:
            def __init__(self):
                def row(id, name, role, password):
                    return dict(user_id=id, username=name, full_name=name.title(), role=role,
                                is_active=1, password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt(4)).decode())
                self.records = {
                    'admin_test': row(1, 'admin_test', 'admin', 'Admin1234!'),
                    'user_test': row(2, 'user_test', 'user', 'User12345!'),
                }
            def find_by_username(self, username):
                return self.records.get(username)
            def find_by_id(self, uid):
                return next((r for r in self.records.values() if r['user_id'] == uid), None)
            def list_users(self):
                return list(self.records.values())
            def create_user(self, username, full_name, hashed, role):
                uid = max(r['user_id'] for r in self.records.values()) + 1
                self.records[username] = dict(user_id=uid, username=username, full_name=full_name,
                                               role=role, is_active=1, password_hash=hashed)
                return uid
            def set_active(self, uid, active, actor):
                record = self.find_by_id(uid)
                if record is None: raise ValueError('Unknown user')
                if uid == actor and not active: raise ValueError('Cannot lock yourself')
                if record['role'] == 'admin' and not active and sum(
                        r['role'] == 'admin' and r['is_active'] for r in self.records.values()) <= 1:
                    raise ValueError('Last active admin')
                record['is_active'] = int(active)
        dao = MemoryDAO()
        auth = AuthService(dao)
        return auth, dao, AuthenticationError, AuthorizationError, bcrypt

    def db(self):
        if not self.args.db: skip('Cần --db và ui_app/.env; chỉ kiểm tra SELECT, không ghi')
        if self._db is not None: return self._db
        optional_import('mysql')
        from dao.database import get_connection
        try:
            self._db = get_connection()
        except Exception as exc:
            skip(f'MySQL không sẵn sàng: {type(exc).__name__}: {exc}')
        return self._db

    def query(self, sql, params=()):
        conn = self.db()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(sql, params)
            return cur.fetchall()
        finally:
            cur.close()

    def populated(self):
        n = self.query('SELECT COUNT(*) n FROM customers')[0]['n']
        if not n: skip('MySQL chưa import dữ liệu thật; bảng customers trống')

    def model(self):
        if self._model is not None: return self._model
        optional_import('numpy')
        optional_import('pandas')
        for rel in ('customer_segmentation/outputs/kmeans_model.joblib',
                    'customer_segmentation/outputs/rfm_scaler.joblib',
                    'customer_segmentation/outputs/model_info.joblib',
                    'customer_segmentation/datasets/processed/customer_clusters.csv'):
            self.require_file(rel)
        from services.rfm_model_service import RFMModelService
        self._model = RFMModelService()
        return self._model

    def qt(self):
        if not self.args.gui: skip('Cần --gui để chạy giao diện PyQt6 (offscreen)')
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PyQt6.QtWidgets import QApplication
        self._qapp = QApplication.instance() or QApplication([])
        return self._qapp

    def sample_raw(self):
        pd = optional_import('pandas')
        rows = [
            ('10001', '85123', 'Product', 2, '2011-12-01', 10., 1001, 'UK'),
            ('C10002', '85123', 'Product', -1, '2011-12-02', 10., 1001, 'UK'),
            ('10003', '85124', 'Item', 1, '2011-12-03', 20., 1002, 'France'),
            ('C10004', '85125', 'Unmatched', -1, '2011-12-04', 5., 1003, 'UK'),
        ]
        from preprocessing.data_preprocessor import COLUMNS
        df = pd.DataFrame(rows, columns=COLUMNS)
        df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
        return df

    def rfm_sample(self):
        pd = optional_import('pandas')
        from rfm.rfm_analyzer import RFMAnalyzer
        data = pd.DataFrame([
            (1001, '10001', '2011-12-01', 20.),
            (1001, 'C10002', '2011-12-02', -10.),
            (1002, '10003', '2011-12-03', 20.),
            (1003, 'C10004', '2011-12-04', -5.),
            (1004, '10005', '2011-12-02', 5.),
            (1004, 'C10006', '2011-12-03', -5.),
        ], columns=['customer_id', 'invoice_no', 'invoice_date', 'total_amount'])
        data['invoice_date'] = pd.to_datetime(data['invoice_date'])
        analyzer = RFMAnalyzer(data)
        data = analyzer.calculate_rfm()
        return analyzer, data

    # ---- AUTH & ACCOUNT: actual AuthService with isolated in-memory DAO ----
    def account(self, cid):
        auth, dao, AE, AZ, bcrypt = self.auth()
        def throws(exc, fn, *a):
            try: fn(*a)
            except exc: return
            raise AssertionError(f'Expected {exc.__name__}')
        if cid == 'AUTH-01':
            r = auth.login('admin_test', 'Admin1234!')
            require(r['role'] == 'admin' and auth.require_admin().user_id == 1, 'Admin login/permission')
        elif cid == 'AUTH-02':
            require(auth.login('user_test','User12345!')['role'] == 'user', 'User role')
        elif cid == 'AUTH-03':
            throws(AE, auth.login, 'admin_test', 'bad'); require(auth.current_user is None,'Session leaked')
        elif cid == 'AUTH-04':
            for u,p in [('', ''),('', '123'),('user_test','')]: throws(AE,auth.login,u,p)
            require(auth.current_user is None,'Unexpected session')
        elif cid == 'AUTH-05':
            dao.records['user_test']['is_active'] = 0
            throws(AE,auth.login,'user_test','User12345!')
        elif cid == 'AUTH-06':
            auth.login('admin_test','Admin1234!');auth.logout()
            require(auth.current_user is None,'Session retained');throws(AZ,auth.require_admin)
        elif cid == 'AUTH-07':
            auth.login('user_test','User12345!');throws(AZ,auth.require_admin);throws(AZ,auth.list_users)
        elif cid == 'AUTH-08':
            auth.login('admin_test','Admin1234!');dao.records['admin_test']['role']='user'
            throws(AZ,auth.require_admin);require(auth.current_user is None,'Admin session retained')
        elif cid == 'AUTH-09':
            auth.login('admin_test','Admin1234!')
            auth.add_user('created_test','Created Tester','Password123!','user')
            h=dao.records['created_test']['password_hash']
            require(h != 'Password123!' and bcrypt.checkpw(b'Password123!',h.encode()),'bcrypt hash')
        elif cid == 'AUTH-10':
            src=self.source('ui_app/dao/database.py');ign=self.source('.gitignore')
            require('load_dotenv' in src and 'DB_PASSWORD' in src and '.env' in ign,'Credentials setup')
            ignore=subprocess.run(['git','check-ignore','-q','ui_app/.env'],cwd=ROOT)
            require(ignore.returncode==0,'ui_app/.env is not ignored by Git')
        elif cid == 'USER-01':
            auth.login('admin_test','Admin1234!');require(len(auth.list_users())==2,'Admin list')
        elif cid in ('USER-02','USER-03'):
            role='admin' if cid=='USER-03' else 'user'
            auth.login('admin_test','Admin1234!')
            auth.add_user('new_tester','New Tester','Valid12345!',role)
            record=dao.records['new_tester']
            require(record['role']==role and record['is_active']==1,'Created account')
            require(bcrypt.checkpw(b'Valid12345!',record['password_hash'].encode()),'Hash')
        elif cid == 'USER-04':
            auth.login('admin_test','Admin1234!')
            throws(ValueError,auth.add_user,'user_test','Dup Tester','Valid12345!','user')
            require(len(dao.records)==2,'Duplicate created')
        elif cid == 'USER-05':
            auth.login('admin_test','Admin1234!')
            for name in ('a','bad name','x'*51):
                throws(ValueError,auth.add_user,name,'User','Valid12345!','user')
        elif cid in ('USER-06','USER-07'):
            auth.login('admin_test','Admin1234!')
            auth.set_user_active(2,False)
            require(dao.records['user_test']['is_active']==0,'Lock not persisted')
            throws(AE,auth.login,'user_test','User12345!')
            if cid=='USER-07':
                auth.login('admin_test','Admin1234!'); auth.set_user_active(2,True)
                require(auth.login('user_test','User12345!')['role']=='user','Unlock failed')
        elif cid=='USER-08':
            # Real UserDAO must reject self-lock, not merely an in-memory fake.
            code=self.source('ui_app/auth/user_dao.py')
            require('actor_id' in code and ('tự khóa' in code or 'tu khoa' in code), 'Self-lock protection absent')
            skip('Cần test DB riêng để xác minh UserDAO.set_active thực tế, không ghi lên MySQL thật')
        elif cid=='USER-09':
            code=self.source('ui_app/auth/user_dao.py')
            require('Admin' in code and ('cuối cùng' in code or 'cuoi cung' in code),'Last admin protection absent')
            skip('Cần database sandbox chỉ có một Admin để xác minh thao tác cuối cùng')
        else: skip('Account test not implemented')

    # ---- Read-only SQL integration; independently compared with DAO/service ----
    def database(self, cid):
        self.db()
        for rel in ('customer_segmentation/outputs/kmeans_model.joblib',
                    'customer_segmentation/outputs/rfm_scaler.joblib',
                    'customer_segmentation/outputs/model_info.joblib',
                    'customer_segmentation/datasets/processed/customer_clusters.csv'):
            self.require_file(rel)
        from services import db_service
        if cid=='DB-01':
            names={r['TABLE_NAME'] for r in self.query("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE()")}
            require({'users','segments','customers','products','invoices','invoice_details','rfm_profiles','customer_segments'}<=names,'Missing tables')
            fk=self.query("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA=DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL")
            require(len(fk)>=5,'Foreign keys missing')
        elif cid=='DB-02':
            require(self.query('SELECT 1 n')[0]['n']==1,'MySQL SELECT 1')
        elif cid=='DB-05':
            self.populated()
            r=self.query('SELECT (SELECT COUNT(*) FROM rfm_profiles) a,(SELECT COUNT(*) FROM customer_segments) b')[0]
            require(r['a']==r['b'],'RFM and segments count disagree')
            n=self.query('SELECT COUNT(*) n FROM rfm_profiles r LEFT JOIN customer_segments s USING(customer_id) WHERE s.customer_id IS NULL')[0]['n']
            require(n==0,'RFM customer IDs disagree')
        elif cid.startswith('DASH-'):
            self.populated()
            stats=db_service.get_dashboard_stats()
            sql=self.query('''SELECT (SELECT COUNT(DISTINCT customer_id) FROM invoices) total_customers,
                (SELECT COUNT(*) FROM invoices) total_invoices,
                (SELECT COALESCE(SUM(total_amount),0) FROM invoice_details) total_revenue,
                (SELECT COUNT(*) FROM segments) num_segments''')[0]
            for field in ('total_customers','total_invoices','total_revenue','num_segments'):
                require(abs(float(stats[field])-float(sql[field])) < 0.02,f'KPI {field} differs')
            if cid=='DASH-02':
                months=db_service.get_monthly_revenue()
                require(months==sorted(months) and bool(months),'Monthly revenue order')
                month_sql=self.query('''SELECT DATE_FORMAT(i.invoice_date,'%Y-%m') m, SUM(d.total_amount) amount
                    FROM invoice_details d JOIN invoices i USING(invoice_no) GROUP BY m ORDER BY m''')
                require(len(months)==len(month_sql),'Monthly groups mismatch')
                for a,b in zip(months,month_sql):
                    require(a[0]==b['m'] and abs(a[1]-float(b['amount']))<0.02,'Monthly amount mismatch')
            elif cid=='DASH-03':
                rows=self.query('SELECT cluster, COUNT(*) n FROM customer_segments GROUP BY cluster')
                require(len(rows)==2 and sum(r['n'] for r in rows)==self.query('SELECT COUNT(*) n FROM customer_segments')[0]['n'],'Cluster distribution')
            elif cid=='DASH-05':
                r=self.query('SELECT COUNT(*) n FROM rfm_profiles')[0]['n']
                require(stats['total_customers']>=r,'More RFM than purchasing customers')
            elif cid=='DASH-01':
                skip('KPI SQL đã đối chiếu; để xác nhận 4 thẻ hiển thị cần chạy thêm --gui')
        elif cid.startswith('DATA-'):
            self.populated()
            from dao.transaction_dao import TransactionDAO
            dao=TransactionDAO()
            if cid=='DATA-01':
                from ui.pages.TransactionDataPageEx import HEADERS
                require(len(HEADERS)==9,'Transaction table does not have 9 headers')
                result=dao.get_transactions(page=1,page_size=1)
                require(len(result['rows'])==1 and len(result['rows'][0])==9,'Wrong table columns')
            elif cid in ('DATA-02','DATA-03'):
                sample=self.query('SELECT invoice_no,customer_id,stock_code FROM invoices i JOIN invoice_details d USING(invoice_no) LIMIT 1')[0]
                values=[sample['invoice_no']] if cid=='DATA-02' else [str(sample['customer_id']),sample['stock_code']]
                for kw in values:
                    result=dao.get_transactions(keyword=kw,page_size=100)
                    require(result['total_rows']>0,'Expected keyword result')
                    require(all(kw.lower() in ' '.join(str(v).lower() for v in r.values()) for r in result['rows']),'Keyword mismatch')
            elif cid=='DATA-04':
                country=dao.get_countries()[0]
                result=dao.get_transactions(country=country,page_size=50)
                require(result['total_rows']>0 and all(r['country']==country for r in result['rows']),'Country filter wrong')
            elif cid=='DATA-05':
                d=self.query('SELECT DATE(MIN(invoice_date)) d FROM invoices')[0]['d']
                result=dao.get_transactions(date_from=d,date_to=d,page_size=200)
                require(result['total_rows']>0,'Date boundary excluded')
                require(all(r['invoice_date'].date()==d for r in result['rows']),'Date boundary leaked')
            elif cid=='DATA-07':
                for size in (25,50,100):
                    r=dao.get_transactions(page=1,page_size=size)
                    require(len(r['rows'])==min(size,r['total_rows']),'Incorrect page size')
            elif cid=='DATA-08':
                a=dao.get_transactions(page=1,page_size=25); b=dao.get_transactions(page=2,page_size=25)
                require(a['total_rows']==b['total_rows'] and abs(a['total_amount']-b['total_amount'])<0.01,'Totals differ by page')
            elif cid=='DATA-09':
                r=dao.get_transactions(keyword='__QA_NO_RESULTS_9A81B2__')
                require(r['total_rows']==0 and r['rows']==[] and r['total_amount']==0,'Empty result behavior')
            else:skip('DATA-06 requires GUI')
        elif cid.startswith('RFM-'):
            self.populated()
            if cid in ('RFM-01','RFM-02','RFM-03'):
                from dao.rfm_dao import RFMDAO
                dao=RFMDAO(); result=dao.get_rfm_table(page=1,page_size=50)
                require(bool(result['rows']),'RFM table empty')
                if cid=='RFM-01':
                    row=result['rows'][0]; db=self.query('SELECT recency,frequency,monetary FROM rfm_profiles WHERE customer_id=%s',(row['customer_id'],))[0]
                    for k in ('recency','frequency','monetary'):
                        require(abs(float(row[k])-float(db[k]))<0.01,f'RFM {k} mismatch')
                elif cid=='RFM-02':
                    uid=result['rows'][0]['customer_id'];r=dao.get_rfm_table(keyword=str(uid))
                    require(any(x['customer_id']==uid for x in r['rows']),'Customer search')
                elif cid=='RFM-03':
                    cluster=result['rows'][0]['cluster'];r=dao.get_rfm_table(cluster=cluster)
                    require(all(x['cluster']==cluster for x in r['rows']),'Cluster filter')
            else:skip('RFM GUI test requires --gui')
        elif cid.startswith('SEG-') or cid.startswith('CL-') or cid.startswith('MKT-'):
            self.populated()
            if cid=='SEG-01':
                seg=db_service.get_segments();require(len(seg)==2,'Must have two segments')
            elif cid=='SEG-02':
                seg=db_service.get_cluster_profiles();require(len(seg)==2,'Cluster profile missing')
            elif cid=='SEG-04':
                uid=self.query('SELECT customer_id FROM customer_segments LIMIT 1')[0]['customer_id']
                r=db_service.get_segment_customers(keyword=str(uid))
                require(any(x['customer_id']==uid for x in r['rows']),'Customer filter')
            elif cid=='SEG-05':
                c=db_service.get_customer_countries()[0]
                r=db_service.get_segment_customers(country=c)
                require(all(x['country']==c for x in r['rows']),'Country filter')
            elif cid=='SEG-06':
                for mode,field,reverse in [('monetary_desc','monetary',True),('frequency_desc','frequency',True),('recency_asc','recency',False)]:
                    r=db_service.get_segment_customers(sort_by=mode,page_size=100)
                    arr=[float(x[field]) for x in r['rows']]
                    require(arr==sorted(arr,reverse=reverse),'Bad sort '+mode)
            elif cid=='SEG-07':
                a=db_service.get_segment_customers(page=1,page_size=50)
                b=db_service.get_segment_customers(page=2,page_size=50)
                require(a['total_rows']==b['total_rows'] and not ({x['customer_id'] for x in a['rows']} & {x['customer_id'] for x in b['rows']}),'Pagination overlap')
            elif cid=='CL-01':
                r=db_service.get_cluster_profiles();require(len(r)==2,'Two cluster profiles')
            elif cid=='CL-02':
                r=self.query('SELECT cluster,SUM(r.monetary) revenue FROM customer_segments c JOIN rfm_profiles r USING(customer_id) GROUP BY cluster')
                require(len(r)==2 and sum(float(x['revenue']) for x in r)>0,'RFM net revenue by segment')
            elif cid=='MKT-01':
                r=db_service.get_segments();require(all(x.get('marketing_strategy') for x in r),'Marketing strategy absent')
            elif cid=='MKT-02':
                r=db_service.get_marketing_actions(0)
                require(bool(r),'No marketing actions')
            else:
                skip('Tương tác/CSV GUI cần --gui hoặc kiểm thử thủ công, không được tự nhận PASS')
        else: skip('DB scenario requires explicit environment')

    def models(self,cid):
        import numpy as np
        m=self.model()
        if cid=='RFM-04':
            info=m.get_model_info();require(m.model.n_clusters==2 and info.get('k')==2,'Wrong K')
        elif cid=='RFM-05':
            ks=[x['k'] for x in m.get_model_info()['k_search']]
            require(ks==list(range(2,11)),'Missing k2..10 metrics')
        elif cid in ('RFM-06','RFM-07','RFM-08','ML-12'):
            vals=(0,1,0) if cid=='RFM-08' else (30,6,2000)
            r=m.predict_segment(*vals)
            import numpy as np
            expected=int(m.model.predict(m.scaler.transform(np.log1p(np.asarray([vals],dtype=float))))[0])
            require(r['cluster']==expected and r['segment_name_en'] in ('High-Value Customers','Low-Activity Customers'),'Model prediction differs')
            if cid=='RFM-07': require(r==m.predict_segment(*vals),'Nondeterministic output')
        elif cid in ('RFM-09','RFM-10','RFM-11'):
            vals={'RFM-09':(-1,1,10),'RFM-10':(10,0,10),'RFM-11':(10,2,-1)}[cid]
            try: m.predict_cluster(*vals)
            except ValueError: return
            raise AssertionError('Expected ValueError')
        elif cid=='ML-10':
            from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
            df=m.customer_clusters; X=m.scaler.transform(np.log1p(df[['recency','frequency','monetary']].to_numpy(float)))
            labels=m.model.predict(X)
            require(len(set(labels))==2,'Expected K=2')
            info=m.get_model_info()
            for k,f in [('silhouette',silhouette_score),('davies_bouldin',davies_bouldin_score),('calinski_harabasz',calinski_harabasz_score)]:
                if k in info:
                    require(abs(float(info[k])-float(f(X,labels)))<max(0.1,abs(float(info[k]))*0.05),k+' mismatch')
        elif cid=='ML-11':
            files=[self.require_file('customer_segmentation/outputs/'+x) for x in ('kmeans_model.joblib','rfm_scaler.joblib','model_info.joblib')]
            before=[hashlib.sha256(f.read_bytes()).hexdigest() for f in files]
            from models.cluster_evaluation import load_saved_model
            load_saved_model()
            require(before==[hashlib.sha256(f.read_bytes()).hexdigest() for f in files],'Saved model modified')
        elif cid=='ML-14':
            import services.rfm_model_service as mod
            with tempfile.TemporaryDirectory() as d,patch.object(mod,'MODEL_PATH',Path(d)/'absent.joblib'):
                try:mod.RFMModelService()
                except FileNotFoundError:return
            raise AssertionError('Missing artefact silently accepted')
        else:skip('Unknown model scenario')

    def ml(self,cid):
        pd=optional_import('pandas')
        import numpy as np
        from preprocessing.data_preprocessor import prepare_transactions, net_returns, customer_summary
        from rfm.rfm_analyzer import RFMAnalyzer
        if cid=='ML-01':
            d=self.sample_raw().drop(columns=['InvoiceNo'])
            try: prepare_transactions(d)
            except ValueError as e:
                require('InvoiceNo' in str(e),'Error does not identify missing column');return
            raise AssertionError('Missing column accepted')
        if cid=='ML-02':
            x=self.sample_raw();x=pd.concat([x,x.iloc[:1]],ignore_index=True)
            x.loc[len(x)] = x.iloc[1].copy()
            x.loc[len(x)-1,'CustomerID']=None
            clean,steps,rejected=prepare_transactions(x)
            require(len(clean)==4,'Dedup/invalid customer failed')
            require({'exact_duplicate','missing_or_invalid_customer'} <= set(rejected['Reason']),'Missing rejected reasons')
        if cid=='ML-03':
            transactions,_,_=prepare_transactions(self.sample_raw())
            net,links=net_returns(transactions)
            require((net['Quantity']<0).sum()==1,'Unmatched refund dropped')
            require(abs(net['TotalAmount'].sum()-transactions['TotalAmount'].sum())<1e-8,'Net spending changed')
        if cid in ('ML-04','ML-05','ML-06','ML-07','ML-08'):
            analyzer,df=self.rfm_sample()
            first=df.set_index('customer_id')
            if cid=='ML-04':require(first.loc[1001,'recency']==4 and first.loc[1001,'frequency']==1,'Purchase-only recency/frequency')
            elif cid=='ML-05':require(first.loc[1001,'monetary']==10.,'Refund missing from Monetary')
            elif cid=='ML-06':
                excluded=set(analyzer.excluded_df['customer_id'])
                require({1003,1004}<=excluded and {1003,1004}.isdisjoint(first.index),'Nonpositive/net-only RFM')
            elif cid=='ML-07':require(str(analyzer.reference_date.date())=='2011-12-05','Reference date != last+1')
            else:
                log=analyzer.apply_log_transform(); scaled=analyzer.fit_scaler()
                expected=np.log1p(df[['recency','frequency','monetary']].to_numpy(float))
                require(np.allclose(log[['recency_log','frequency_log','monetary_log']],expected),'Bad log1p')
                transform=analyzer.transform_new(df[['recency','frequency','monetary']])
                require(np.allclose(transform,scaled[['recency_scaled','frequency_scaled','monetary_scaled']]),'Bad scaler')
        elif cid=='ML-09':
            from sklearn.cluster import KMeans
            from sklearn.metrics import silhouette_score
            rng=np.random.default_rng(42)
            X=np.vstack([rng.normal(0,.1,(20,3)),rng.normal(3,.1,(20,3))])
            result=[]
            for k in range(2,11):
                m=KMeans(n_clusters=k,random_state=42,n_init=10).fit(X)
                result.append((k,float(m.inertia_),float(silhouette_score(X,m.labels_))))
            require(len(result)==9 and result[0][0]==2,'K scan incomplete')
            require(KMeans(n_clusters=2,random_state=42,n_init=10).fit(X).n_clusters==2,'Final K')
        elif cid=='ML-13':
            from database.import_mysql import align_to_segments
            rfm=pd.DataFrame({'customer_id':[1,2,3,4],'monetary':[100.,80.,2.,4.]})
            labels=pd.Series([1,1,0,0],index=rfm['customer_id'])
            segs=pd.DataFrame({'cluster':[0,1],'segment_name_en':['High-Value Customers','Low-Activity Customers']})
            mapped=align_to_segments(rfm,labels,segs)
            require(mapped.tolist()==[0,0,1,1],'High-value mapping misaligned')
        else:skip('ML case requires model artifact or is not implemented')

    def security(self,cid):
        if cid=='SEC-01':
            for command in ([sys.executable,str(UI/'main.py'),'--demo'],
                            [sys.executable,str(ROOT/'launcher.py'),'--demo']):
                p=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=15)
                require(p.returncode==2,'Demo entry point did not reject: '+repr(command))
                require('Demo' in (p.stdout+p.stderr),'No demo rejection message')
        elif cid=='SYS-01':
            from services.safe_service import SafeService
            from dao.database import DatabaseError
            from services import db_health
            class Broken:
                def get_dashboard_stats(self):raise DatabaseError('QA simulated outage')
            service=SafeService(Broken(),fallback=None)
            try: service.get_dashboard_stats()
            except DatabaseError: pass
            else:raise AssertionError('Swallowed DB outage / demo fallback')
            require(service.status==db_health.OFFLINE,'Offline status missing')
        elif cid=='SYS-02':
            from services.safe_service import SafeService
            from services import db_health
            with patch.object(db_health,'check_database',side_effect=[(db_health.EMPTY,'empty'),(db_health.OK,'')]):
                service=SafeService(object(),fallback=None)
                require(service.check()==db_health.EMPTY,'EMPTY status absent')
                require(service.check()==db_health.OK,'Recovery status absent')
            skip('Chỉ xác minh trạng thái SafeService; luồng Retry giao diện cũ đã bị bỏ')
        elif cid=='ARCH-01':
            required=['ui_app/main.py','ui_app/auth/auth_service.py','ui_app/services/db_service.py',
                      'ui_app/dao/database.py','customer_segmentation/rfm/rfm_analyzer.py',
                      'customer_segmentation/models/clustering_model.py']
            require(all((ROOT/p).is_file() for p in required),'Missing architecture files')
            s=self.source('ui_app/services/__init__.py')
            require('db_service as _data_service' in s and 'fallback=None' in s,'Not MySQL-only service')
        elif cid=='ARCH-02':
            files=['ui_app/auth/auth_service.py','ui_app/dao/transaction_dao.py',
                   'customer_segmentation/rfm/rfm_analyzer.py']
            for f in files:
                code=ast.parse(self.source(f))
                for node in ast.walk(code):
                    if isinstance(node,ast.ClassDef):require(node.name[0].isupper(),f'Class casing: {f}:{node.name}')
                    elif isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                        require(bool(re.fullmatch(r'[a-z_][a-z0-9_]*',node.name)),f'Function casing: {f}:{node.name}')
        elif cid=='DATA-06':
            s=self.source('ui_app/ui/pages/TransactionDataPageEx.py')
            require('dateFrom.date() > self.dateTo.date()' in s and 'QMessageBox.warning' in s,'No date validation')
            skip('Kiểm tra giao diện phải chạy --gui; static guard hiện diện, chưa xác nhận hộp thoại')
        elif cid=='SYS-03':skip('Cần chạy GUI và điều hướng 6 trang trong môi trường có MySQL')
        else:skip('Unsupported static case')

    def gui_case(self, cid):
        self.qt()
        from PyQt6.QtWidgets import QFileDialog
        from PyQt6.QtCore import QDate
        from datetime import datetime as dt

        class Transactions:
            calls = 0
            def get_countries(self): return ['United Kingdom']
            def get_dashboard_stats(self):
                return {'date_from':dt(2011,12,1), 'date_to':dt(2011,12,9)}
            def get_transactions(self, **kwargs):
                self.calls += 1
                return {'rows':[dict(invoice_no='123',invoice_date=dt(2011,12,1),
                    customer_id=1,country='United Kingdom',stock_code='ITEM',description='Item',
                    quantity=1,unit_price=2.,total_amount=2.)], 'total_rows':1,'total_amount':2.}
        if cid in ('DATA-01','DATA-06'):
            from ui.pages.TransactionDataPageEx import TransactionDataPageEx
            stub=Transactions(); w=TransactionDataPageEx(stub)
            try:
                if cid=='DATA-01':
                    require(w.tblTransactions.columnCount()==9,'UI does not have 9 columns')
                    require(w.tblTransactions.rowCount()==1,'UI rows missing')
                    require(w.tblTransactions.item(0,8).text()=='2.00','Wrong amount display')
                else:
                    w.dateFrom.setDate(QDate(2011,12,8));w.dateTo.setDate(QDate(2011,12,2))
                    previous=stub.calls
                    with patch('ui.pages.TransactionDataPageEx.QMessageBox.warning') as warning:
                        w.search()
                    require(warning.call_count==1,'Invalid date not warned')
                    require(stub.calls==previous,'Invalid filter queried database')
            finally:w.close()
            return
        if cid in ('MKT-03','MKT-06'):
            from ui.pages.ClusterMarketingPageEx import ClusterMarketingPageEx
            def profile(cluster,name):
                return dict(cluster=cluster,segment_name_en=name,segment_name=name,color='#228822',
                    customers=10,customer_pct=50.,revenue=100.,revenue_pct=50.,
                    invoices=12,recency_mean=10.,recency_median=9.,frequency_mean=2.,
                    frequency_median=2.,monetary_mean=10.,monetary_median=9.,
                    avg_invoice_value=8.,one_time_pct=20.,recency_le_30_pct=75.,
                    recency_gt_90_pct=10.,recency_gt_180_pct=5.,tenure_median=99.,silhouette_mean=.4)
            class Marketing:
                exports=0
                def get_cluster_profiles(self):return [profile(0,'High-Value Customers'),profile(1,'Low-Activity Customers')]
                def get_segments(self):return [dict(cluster=c,segment_name_en=p['segment_name_en'],
                    marketing_strategy='Strategy') for c,p in enumerate(self.get_cluster_profiles())]
                def get_cluster_centroids(self):return {'features':['R','F','M'],'centroids':{0:[1,2,3],1:[-1,-2,-3]}}
                def get_marketing_actions(self,cluster):return [dict(title='Target',description='Desc',
                    kpi='Customer return',target={'min_frequency':6})]
                def get_segment_customers(self,**kwargs):return {'rows':[],'total_rows':5}
                def export_customers_csv(self,*args,**kwargs):self.exports+=1;return 0
            stub=Marketing(); w=ClusterMarketingPageEx(stub)
            try:
                if cid=='MKT-03':
                    received=[]
                    w.view_customers_requested.connect(lambda cluster,target,title:received.append((cluster,target,title)))
                    w.view_target()
                    require(len(received)==1 and received[0][1].get('min_frequency')==6,'Target signal lost')
                else:
                    with patch('ui.pages.ClusterMarketingPageEx.QFileDialog.getSaveFileName',return_value=('','')):
                        w.export_target()
                    require(stub.exports==0,'Canceled export wrote data')
            finally:w.close()
            return
        skip('Chưa có bộ thao tác giao diện an toàn cho case này; cần QA thực thi thực tế')

    def run_case(self, cid):
        try:
            if cid.startswith(('AUTH-','USER-')):self.account(cid)
            elif cid in ('DATA-01','DATA-06','MKT-03','MKT-06'):
                self.gui_case(cid)
            elif cid=='DB-03':
                if not self.args.slow: skip('Dùng --slow để chạy dry-run dữ liệu sạch (chỉ đọc)')
                cmd=[sys.executable,str(ML/'database/import_mysql.py'),'--dry-run']
                run=subprocess.run(cmd,cwd=ML,capture_output=True,text=True,timeout=900,env={**os.environ,'PYTHONUTF8':'1'})
                require(run.returncode==0 and 'Dry run:' in run.stdout,'Import dry-run failed: '+run.stderr[-900:])
            elif cid=='DB-04':
                skip('GHI DB: yêu cầu sandbox MySQL riêng đã backup. Không tự xóa 6 bảng để test')
            elif cid.startswith(('DASH-','DATA-','SEG-','CL-','MKT-','DB-')) or cid in ('RFM-01','RFM-02','RFM-03'):
                self.database(cid)
            elif cid in ('RFM-04','RFM-05','RFM-06','RFM-07','RFM-08','RFM-09','RFM-10','RFM-11','ML-10','ML-11','ML-12','ML-14'):
                self.models(cid)
            elif cid.startswith('ML-'):self.ml(cid)
            else:self.security(cid)
            partial={'AUTH-01','AUTH-02','AUTH-06','USER-01','USER-02','USER-03','USER-06','USER-07',
                     'DASH-03','DASH-05','SEG-01','SEG-02','SEG-04','SEG-05','SEG-06','SEG-07',
                     'CL-01','CL-02','MKT-01','MKT-02','ML-09','ML-07','SYS-01','RFM-04','RFM-05'}
            if cid in partial:
                return 'SKIP','Đã xác minh một phần bằng assert; chưa chứng minh toàn bộ thao tác GUI/DB theo Excel'
            return 'PASS','Verified by executable assertion'
        except NeedsEnvironment as exc:
            return 'SKIP',str(exc)
        except Exception as exc:
            return 'FAIL',f'{type(exc).__name__}: {exc}\n'+traceback.format_exc(limit=3)

    def run(self):
        matrix=json.loads((Path(__file__).with_name('matrix.json')).read_text(encoding='utf-8'))
        cases=matrix['cases']; flows=matrix['flows']
        require(len(cases)==87 and len(flows)==7 and sum(len(v['steps']) for v in flows.values())==26,'Test matrix count mismatch')
        for case in cases:
            cid=case['id'];status,message=self.run_case(cid)
            self.results[cid]={'status':status,'name':case['name'],'detail':message}
            if not self.args.quiet:print(f'{cid:<9} {status:<4}  {case["name"]}'+(' — '+message.splitlines()[0] if status!='PASS' else ''))
        # A flow is NOT claimed to pass just because its member tests pass:
        # an end-to-end UI sequence must be executed and verified in a separate test run.
        flow_results={}
        for fid,flow in flows.items():
            related=[cid for step in flow['steps'] for cid in step['cases']]
            missing=[cid for cid in related if cid not in self.results]
            failures=[cid for cid in related if self.results.get(cid,{}).get('status')=='FAIL']
            blocked=[cid for cid in related if self.results.get(cid,{}).get('status')=='SKIP']
            status='FAIL' if failures or missing else 'NOT_RUN'
            flow_results[fid]={'name':flow['name'],'status':status,'steps':len(flow['steps']),
                               'reason':'Có TC lỗi: '+', '.join(failures+missing) if status=='FAIL'
                                        else 'Chưa thực thi tương tác E2E tuần tự; không được suy từ TC PASS',
                               'blocked_cases':blocked}
        summary={s:sum(r['status']==s for r in self.results.values()) for s in ('PASS','FAIL','SKIP')}
        output={'created_at':datetime.now().isoformat(timespec='seconds'),'source':matrix['source'],
                'summary':summary,'cases':self.results,'flows':flow_results,
                'note':'NOT_RUN của luồng không phải PASS; test có DB GUI cần chạy trong môi trường riêng.'}
        if self.args.report:
            path=Path(self.args.report);path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
            print('Report:',path)
        print(f"\n87 TC: PASS={summary['PASS']}, FAIL={summary['FAIL']}, SKIP={summary['SKIP']}; "
              f"7 luồng: " + ', '.join(f'{k}={v["status"]}' for k,v in flow_results.items()))
        if self._db is not None: self._db.close()
        return 1 if summary['FAIL'] or (self.args.strict and (summary['SKIP'] or any(f['status']!='PASS' for f in flow_results.values()))) else 0


def main():
    p=argparse.ArgumentParser(description='RFM Insight 87 cases / 7 E2E flows; safe by default')
    p.add_argument('--db',action='store_true',help='Read-only SELECT against MySQL from ui_app/.env')
    p.add_argument('--gui',action='store_true',help='Enable offscreen Qt checks (when implemented)')
    p.add_argument('--slow',action='store_true',help='Enable slow checks (if supported)')
    p.add_argument('--strict',action='store_true',help='Non-zero exit on ANY skipped case or unexecuted flow')
    p.add_argument('--report',default='qa/results.json',help='JSON report location; ignored in Git')
    p.add_argument('--quiet',action='store_true')
    args=p.parse_args()
    sys.exit(QA(args).run())


if __name__=='__main__':main()